"""测试序列/编排类动作 handlers（AIAssist_Architecture.md §8 / §10 / AIAssist_ActionCatalog.md §5.6 P5）。

start_test_sequence / pause_test_sequence / stop_test_sequence：
  均为 high 风险，经 UI 注入的受控回调（最终走 orchestrator runner），
  start/pause 需确认；stop 作为安全操作不强制确认（仍写审计）。

P5 测试编排进阶（category=test_config / test_sequence）：
  get_current_test_config   : low，当前页面/orchestrator 配置快照（只读）；
  list_test_steps           : low，orchestrator 节点列表（只读，含 uid/node_type/display_name）；
  get_test_result_summary   : low，最近一次测试结果摘要（行数/字段/状态/耗时）；
  apply_test_config_draft   : high+确认，把 generate_draft 草案经预览确认后落地；
  set_test_variable         : high+确认，设置测试变量/参数（运行中写上下文，运行前写预设池）；
  run_single_step           : high+确认，单步执行指定节点（调试用，序列运行中拒绝）。

草案落地链路：AIService.generate_draft → draft_ready → DraftRegistry 登记 draft_id →
AI 调 apply_test_config_draft(draft_id) → ActionDispatcher 确认闭环 → apply 回调落地。
草案绝不自动应用。本模块禁 import Qt。
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.registry import (
    CATEGORY_TEST_CONFIG,
    CATEGORY_TEST_SEQUENCE,
    ActionSpec,
)
from core.ai.schemas import CONFIG_DRAFT, ConfigDraft
from log_config import get_logger

logger = get_logger(__name__)

_EMPTY_SCHEMA = {"type": "object", "properties": {}}

SPECS: list[ActionSpec] = [
    ActionSpec(
        name="start_test_sequence",
        description="启动当前页面的测试序列（高风险，需确认；经 orchestrator runner）。",
        parameters_schema=_EMPTY_SCHEMA,
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_TEST_SEQUENCE,
    ),
    ActionSpec(
        name="pause_test_sequence",
        description="暂停/恢复当前运行的测试序列（高风险，需确认）。",
        parameters_schema=_EMPTY_SCHEMA,
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_TEST_SEQUENCE,
    ),
    ActionSpec(
        name="stop_test_sequence",
        description="停止当前运行的测试序列（安全操作）。",
        parameters_schema=_EMPTY_SCHEMA,
        risk_level="high",
        require_confirmation=False,
        category=CATEGORY_TEST_SEQUENCE,
    ),
    ActionSpec(
        name="get_current_test_config",
        description=(
            "获取当前页面的测试配置快照（Orchestrator 页返回序列节点树 + 仪器连接 meta + "
            "元信息；其它页面返回页面标识与可用性说明）。只读，用于在改动前确认现状。"
        ),
        parameters_schema=_EMPTY_SCHEMA,
        risk_level="low",
        category=CATEGORY_TEST_CONFIG,
    ),
    ActionSpec(
        name="list_test_steps",
        description=(
            "列出当前 Orchestrator 序列的节点步骤（含 uid/node_type/display_name/是否容器/"
            "参数键），供定位单步执行或变量设置的目标。只读。"
        ),
        parameters_schema=_EMPTY_SCHEMA,
        risk_level="low",
        category=CATEGORY_TEST_CONFIG,
    ),
    ActionSpec(
        name="get_test_result_summary",
        description=(
            "获取最近一次测试运行的结果摘要（运行状态/行数/字段名/运行 ID/起止时间/耗时）。"
            "只读，用于判断上一次测试是否通过、产出多少数据。"
        ),
        parameters_schema=_EMPTY_SCHEMA,
        risk_level="low",
        category=CATEGORY_TEST_CONFIG,
    ),
    ActionSpec(
        name="apply_test_config_draft",
        description=(
            "把此前 generate_draft 生成并登记的草案按 draft_id 经预览确认后落地："
            "config_draft 走当前页面配置导入通道，script_draft 走 Orchestrator 画布载入。"
            "高风险，必须确认；草案绝不自动应用。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "draft_id": {
                    "type": "string",
                    "description": "草案句柄，由 generate_draft 产出（形如 draft_001）。",
                },
            },
            "required": ["draft_id"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_TEST_CONFIG,
    ),
    ActionSpec(
        name="generate_config_draft",
        description=(
            "基于当前页配置生成配置草案：读取本页当前配置快照，按 changes 覆盖指定字段"
            "（其余字段保持不变），登记为可引用的 draft_id。本动作不落地、不改控件，"
            "仅产出草案句柄；随后须调 apply_test_config_draft(draft_id) 经用户确认后落地。"
            "用户要求修改本页某些配置参数（如终点电流 end_current_a）时，用本动作生成草案。"
            "changes 的键名须与 get_current_test_config 返回的字段一致。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "changes": {
                    "type": "object",
                    "description": (
                        "要覆盖的配置字段键值对（键名与 get_current_test_config 一致），"
                        "如 {\"end_current_a\": 0.01}。未列出的字段沿用当前值。"
                    ),
                },
                "title": {
                    "type": "string",
                    "description": "草案标题（可选，便于用户在预览中识别）。",
                },
            },
            "required": ["changes"],
        },
        risk_level="low",
        category=CATEGORY_TEST_CONFIG,
    ),
    ActionSpec(
        name="set_test_variable",
        description=(
            "设置测试变量/参数（运行中写入执行上下文变量池，运行前写入预设变量池供下次运行继承）。"
            "高风险，需确认（影响后续测试行为）。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "变量名（字母/数字/下划线，${name} 占位符引用）。",
                },
                "value": {
                    "description": "变量值（字符串/数字/布尔；字符串可含 ${other} 占位符）。",
                },
            },
            "required": ["name", "value"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_TEST_CONFIG,
    ),
    ActionSpec(
        name="run_single_step",
        description=(
            "单步执行 Orchestrator 序列中指定 uid 的节点（调试用，复用 runner 的仪器解析与租约）。"
            "高风险，需确认；序列运行中拒绝以免冲突。"
        ),
        parameters_schema={
            "type": "object",
            "properties": {
                "step_id": {
                    "type": "string",
                    "description": "目标节点 uid（先用 list_test_steps 取得）。",
                },
            },
            "required": ["step_id"],
        },
        risk_level="high",
        require_confirmation=True,
        category=CATEGORY_TEST_SEQUENCE,
    ),
]


def _coerce_variable_value(raw: Any) -> Any:
    """把模型传入的标量值做轻量还原（数字/布尔/字符串）。

    JSON 已把 number/bool/string 还原为对应 Python 类型；此处仅兜底处理
    字符串形态的数字与布尔，便于后续 ${var} 占位符与表达式求值。
    """
    if not isinstance(raw, str):
        return raw
    text = raw.strip()
    if text.lower() in ("true", "false"):
        return text.lower() == "true"
    try:
        if "." in text or "e" in text.lower():
            return float(text)
        return int(text)
    except (TypeError, ValueError):
        return raw


def build_handlers(deps: ActionDeps) -> dict[str, Any]:
    def start_test_sequence(_args: dict) -> dict:
        if deps.test_run_callback is None:
            return {"ok": False, "_message": "当前页面不支持启动测试序列（请切到 Orchestrator）。"}
        ok, message = deps.test_run_callback()
        result = {"ok": bool(ok), "_message": message or ("已启动测试序列。" if ok else "启动失败。")}
        # 登记后台测试任务，供 TaskTray 展示「进行中」并提供停止入口（问题2）。
        if ok:
            registry = deps.pending_task_registry
            if registry is not None:
                session_key = ""
                if deps.session_key_getter is not None:
                    try:
                        session_key = deps.session_key_getter() or ""
                    except Exception:  # noqa: BLE001
                        logger.error("session_key_getter 调用异常", exc_info=True)
                title = str(_args.get("title", "")) if isinstance(_args, dict) else ""
                result["task_id"] = registry.register(
                    session_key, "test_sequence", title=title or "测试序列"
                )
        return result

    def pause_test_sequence(_args: dict) -> dict:
        if deps.test_pause_callback is None:
            return {"ok": False, "_message": "当前页面不支持暂停测试序列。"}
        ok, message = deps.test_pause_callback()
        return {"ok": bool(ok), "_message": message or "已切换暂停/恢复。"}

    def stop_test_sequence(_args: dict) -> dict:
        if deps.test_stop_callback is None:
            return {"ok": False, "_message": "当前页面不支持停止测试序列。"}
        ok, message = deps.test_stop_callback()
        # 停止成功后把对应的后台测试任务标记完成，让 TaskTray「进行中」清零（问题2）。
        if ok:
            registry = deps.pending_task_registry
            if registry is not None:
                session_key = ""
                if deps.session_key_getter is not None:
                    try:
                        session_key = deps.session_key_getter() or ""
                    except Exception:  # noqa: BLE001
                        logger.error("session_key_getter 调用异常", exc_info=True)
                for task in registry.list(session_key=session_key or None):
                    if task.get("kind") == "test_sequence" and task.get("status") == "pending":
                        registry.mark_done(task.get("task_id"), {"stopped": True})
                        registry.mark_consumed(task.get("task_id"))
        return {"ok": bool(ok), "_message": message or "已发送停止请求。"}

    def get_current_test_config(_args: dict) -> dict:
        getter = deps.test_config_getter
        if getter is None:
            return {
                "available": False,
                "_message": "当前未注入测试配置访问器（请切到 Orchestrator 页面）。",
            }
        try:
            snapshot = getter()
        except Exception:  # noqa: BLE001 - 快照失败转可读结果
            logger.error("获取测试配置快照失败", exc_info=True)
            return {"available": False, "_message": "获取配置快照异常，请查看日志。"}
        if not snapshot:
            return {"available": False, "_message": "当前页面无可用测试配置快照。"}
        return snapshot

    def list_test_steps(_args: dict) -> dict:
        getter = deps.test_steps_getter
        if getter is None:
            return {
                "available": False,
                "steps": [],
                "_message": "当前未注入测试步骤访问器（请切到 Orchestrator 页面）。",
            }
        try:
            steps = getter()
        except Exception:  # noqa: BLE001 - 步骤列举失败转可读结果
            logger.error("列举测试步骤失败", exc_info=True)
            return {"available": False, "steps": [], "_message": "列举步骤异常，请查看日志。"}
        if not steps:
            return {"available": True, "steps": [], "_message": "当前序列为空。"}
        return {
            "available": True,
            "step_count": len(steps),
            "steps": steps,
            "_message": f"当前序列共 {len(steps)} 个步骤。",
        }

    def get_test_result_summary(_args: dict) -> dict:
        getter = deps.test_result_summary_getter
        if getter is None:
            return {
                "available": False,
                "_message": "当前未注入测试结果访问器（请切到 Orchestrator 页面）。",
            }
        try:
            summary = getter()
        except Exception:  # noqa: BLE001 - 摘要失败转可读结果
            logger.error("获取测试结果摘要失败", exc_info=True)
            return {"available": False, "_message": "获取结果摘要异常，请查看日志。"}
        if not summary:
            return {"available": False, "_message": "当前无测试结果。"}
        return summary

    def apply_test_config_draft(args: dict) -> dict:
        draft_id = str(args.get("draft_id", "")).strip()
        registry = deps.draft_registry
        if registry is None:
            return {"ok": False, "_message": "草案注册表不可用，无法按 draft_id 落地。"}
        entry = registry.get(draft_id) if draft_id else None
        if entry is None:
            available = registry.list() if hasattr(registry, "list") else []
            # 请求的 draft_id 失效/对不上时，若当前仅存一份草案，回退到该唯一草案：
            # 模型常据残留历史误填旧句柄（如 draft_001），但本会话实际只生成了一份
            # 新草案，此时按唯一草案落地比直接报错更符合用户「确认即应用刚生成的草案」
            # 的预期。存在多份草案则不擅自猜测，仍如实报错让模型/用户明确选择。
            fallback = registry.latest() if len(available) == 1 else None
            if fallback is not None:
                logger.info(
                    "apply_test_config_draft：请求句柄 '%s' 失效，回退到唯一草案 %s",
                    draft_id,
                    fallback.get("draft_id"),
                )
                entry = fallback
                draft_id = fallback.get("draft_id", draft_id)
            else:
                avail_text = (
                    ", ".join(d["draft_id"] for d in available) if available else "（无）"
                )
                return {
                    "ok": False,
                    "draft_id": draft_id,
                    "available_drafts": available,
                    "_message": (
                        f"草案句柄 '{draft_id}' 不存在或已失效。可用草案：{avail_text}。"
                    ),
                }
        kind = entry.get("kind", "")
        payload = entry.get("payload")
        title = entry.get("title", "")

        if kind == "script_draft":
            callback = deps.script_apply_callback
            if callback is None:
                return {
                    "ok": False,
                    "draft_id": draft_id,
                    "_message": "当前页面不支持应用脚本草案（请切到 Orchestrator）。",
                }
            from core.ai.draft_validation import validate_script_draft

            try:
                validation = validate_script_draft(payload)
            except Exception:  # noqa: BLE001 - 校验异常转可读结果
                logger.error("脚本草案校验失败", exc_info=True)
                return {"ok": False, "draft_id": draft_id, "_message": "草案校验异常，请查看日志。"}
            if validation.has_errors:
                return {
                    "ok": False,
                    "draft_id": draft_id,
                    "kind": kind,
                    "title": title,
                    "errors": validation.errors,
                    "_message": "草案校验未通过（error）：" + "; ".join(validation.errors),
                }
            try:
                ok, message = callback(list(validation.nodes))
            except Exception:  # noqa: BLE001 - 落地异常转可读结果
                logger.error("应用脚本草案失败", exc_info=True)
                return {"ok": False, "draft_id": draft_id, "_message": "应用草案异常，请查看日志。"}
            return {
                "ok": bool(ok),
                "draft_id": draft_id,
                "kind": kind,
                "title": title,
                "warnings": validation.warnings,
                "_message": message or ("脚本草案已应用到画布。" if ok else "应用失败。"),
            }

        if kind == "config_draft":
            callback = deps.config_apply_callback
            if callback is None:
                return {
                    "ok": False,
                    "draft_id": draft_id,
                    "_message": "当前页面不支持应用配置草案。",
                }
            try:
                ok, message = callback(payload)
            except Exception:  # noqa: BLE001 - 落地异常转可读结果
                logger.error("应用配置草案失败", exc_info=True)
                return {"ok": False, "draft_id": draft_id, "_message": "应用草案异常，请查看日志。"}
            return {
                "ok": bool(ok),
                "draft_id": draft_id,
                "kind": kind,
                "title": title,
                "_message": message or ("配置草案已应用。" if ok else "应用失败。"),
            }

        return {
            "ok": False,
            "draft_id": draft_id,
            "kind": kind,
            "_message": f"未知草案类型 '{kind}'，无法落地。",
        }

    def set_test_variable(args: dict) -> dict:
        name = str(args.get("name", "")).strip()
        if not name or not name.replace("_", "").isalnum():
            return {"ok": False, "_message": "变量名仅允许字母/数字/下划线且非空。"}
        callback = deps.test_set_variable_callback
        if callback is None:
            return {"ok": False, "_message": "当前页面不支持设置测试变量（请切到 Orchestrator）。"}
        value = _coerce_variable_value(args.get("value"))
        try:
            ok, message = callback(name, value)
        except Exception:  # noqa: BLE001 - 设置异常转可读结果
            logger.error("设置测试变量失败", exc_info=True)
            return {"ok": False, "_message": "设置变量异常，请查看日志。"}
        return {
            "ok": bool(ok),
            "name": name,
            "value": value,
            "_message": message or ("已设置变量。" if ok else "设置变量失败。"),
        }

    def run_single_step(args: dict) -> dict:
        step_id = str(args.get("step_id", "")).strip()
        if not step_id:
            return {"ok": False, "_message": "缺少 step_id（先用 list_test_steps 取得节点 uid）。"}
        callback = deps.test_run_single_step_callback
        if callback is None:
            return {"ok": False, "_message": "当前页面不支持单步执行（请切到 Orchestrator）。"}
        try:
            ok, message = callback(step_id)
        except Exception:  # noqa: BLE001 - 单步异常转可读结果
            logger.error("单步执行失败", exc_info=True)
            return {"ok": False, "_message": "单步执行异常，请查看日志。"}
        return {
            "ok": bool(ok),
            "step_id": step_id,
            "_message": message or ("单步执行已启动。" if ok else "单步执行失败。"),
        }

    def generate_config_draft(args: dict) -> dict:
        registry = deps.draft_registry
        if registry is None:
            return {"ok": False, "_message": "草案注册表不可用，无法生成配置草案。"}
        if deps.config_apply_callback is None:
            return {"ok": False, "_message": "当前页面不支持应用配置草案，生成草案无意义。"}
        getter = deps.test_config_getter
        if getter is None:
            return {"ok": False, "_message": "当前页面不支持读取配置快照，无法生成草案。"}
        changes = args.get("changes")
        if not isinstance(changes, dict) or not changes:
            return {"ok": False, "_message": "缺少 changes（要覆盖的配置字段键值对）。"}
        try:
            current = getter()
        except Exception:  # noqa: BLE001 - 读取异常转可读结果
            logger.error("读取当前配置失败", exc_info=True)
            return {"ok": False, "_message": "读取当前配置异常，请查看日志。"}
        if not isinstance(current, dict):
            current = {}
        unknown = [k for k in changes if k not in current]
        if unknown and current:
            return {
                "ok": False,
                "unknown_keys": unknown,
                "valid_keys": sorted(current.keys()),
                "_message": (
                    f"以下字段不在本页配置中：{', '.join(unknown)}。"
                    f"可用字段：{', '.join(sorted(current.keys()))}。"
                ),
            }
        payload = dict(current)
        payload.update(changes)
        page_key = ""
        if deps.page_key_getter is not None:
            try:
                page_key = deps.page_key_getter() or ""
            except Exception:  # noqa: BLE001
                page_key = ""
        title = str(args.get("title", "")).strip() or "配置草案"
        notes = "由 AI 基于当前配置生成：" + ", ".join(
            f"{k}={changes[k]}" for k in changes
        )
        draft = ConfigDraft(
            target_page=page_key, title=title, notes=notes, payload=payload
        )
        parsed = SimpleNamespace(
            ok=True, payload=draft, kind=CONFIG_DRAFT
        )
        try:
            draft_id = registry.register(parsed)
        except Exception:  # noqa: BLE001 - 登记异常转可读结果
            logger.error("登记配置草案失败", exc_info=True)
            return {"ok": False, "_message": "登记草案异常，请查看日志。"}
        if not draft_id:
            return {"ok": False, "_message": "草案登记失败（无效 payload）。"}
        return {
            "ok": True,
            "draft_id": draft_id,
            "kind": CONFIG_DRAFT,
            "title": title,
            "changes": dict(changes),
            "_message": (
                f"已生成配置草案 {draft_id}（{notes}）。"
                f"请调用 apply_test_config_draft(draft_id=\"{draft_id}\") 经用户确认后落地。"
            ),
        }

    return {
        "start_test_sequence": start_test_sequence,
        "pause_test_sequence": pause_test_sequence,
        "stop_test_sequence": stop_test_sequence,
        "get_current_test_config": get_current_test_config,
        "list_test_steps": list_test_steps,
        "get_test_result_summary": get_test_result_summary,
        "apply_test_config_draft": apply_test_config_draft,
        "generate_config_draft": generate_config_draft,
        "set_test_variable": set_test_variable,
        "run_single_step": run_single_step,
    }
