"""ResponseParser：把模型输出解析为结构化响应（AI_Assist.md §9 / §12）。

双模式（阶段 3 任务 3.1）：
  - 原生 tools 模式：从 message.tool_calls 读取（function.name + arguments）；
  - 降级 JSON 模式：从 content 中提取受约束 JSON（容忍 ```json 围栏 / 前后说明文字）。

解析目标按 kind 区分：
  - log_analysis  -> LogAnalysisResult（沿用阶段 2）
  - config_draft  -> ConfigDraft
  - script_draft  -> ScriptDraft
  - message       -> 纯文本（无结构化载荷）

校验：用轻量 JSON Schema 子集校验（type / required / enum / array items），
失败时给出可读 errors，并可由调用方构造"纠正重试"消息（build_retry_hint）。

本模块纯逻辑，禁 import Qt。不引入 jsonschema 等额外依赖（打包体积铁律）。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from core.ai.schemas import (
    CONFIG_DRAFT,
    CONFIG_DRAFT_SCHEMA,
    ConfigDraft,
    LOG_ANALYSIS_SCHEMA,
    LogAnalysisResult,
    SCRIPT_DRAFT,
    SCRIPT_DRAFT_SCHEMA,
    ScriptDraft,
)
from log_config import get_logger

logger = get_logger(__name__)

KIND_MESSAGE = "message"
KIND_LOG_ANALYSIS = "log_analysis"

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL)
_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class ParsedResponse:
    """结构化解析结果。"""

    kind: str = KIND_MESSAGE
    message: str = ""
    payload: Any = None
    raw: str = ""
    valid: bool = True
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.valid and not self.errors


def _validate(data: Any, schema: dict[str, Any], path: str = "") -> list[str]:
    """轻量 JSON Schema 子集校验：type / required / enum / properties / items。"""
    errors: list[str] = []
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(data, dict):
            errors.append(f"{path or '根'} 应为对象")
            return errors
        for key in schema.get("required", []):
            if key not in data:
                errors.append(f"{path or '根'} 缺少必填字段 '{key}'")
        props = schema.get("properties", {})
        for key, sub_schema in props.items():
            if key in data:
                errors.extend(_validate(data[key], sub_schema, f"{path}.{key}" if path else key))
    elif expected == "array":
        if not isinstance(data, list):
            errors.append(f"{path or '根'} 应为数组")
            return errors
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(data):
                errors.extend(_validate(item, item_schema, f"{path}[{idx}]"))
    elif expected == "string":
        if not isinstance(data, str):
            errors.append(f"{path} 应为字符串")
    elif expected in ("number", "integer"):
        if isinstance(data, bool) or not isinstance(data, (int, float)):
            errors.append(f"{path} 应为数字")
    enum = schema.get("enum")
    if enum is not None and data not in enum:
        errors.append(f"{path} 取值非法（应为 {enum} 之一）")
    return errors


def validate_against_schema(data: Any, schema: dict[str, Any]) -> list[str]:
    """对外暴露的校验入口，返回错误列表（空列表表示通过）。"""
    return _validate(data, schema)


def _extract_json(content: str) -> Any | None:
    """从 content 中提取 JSON（容忍 ```json 围栏 / 前后说明文字）。"""
    if not content:
        return None
    text = content.strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    fence = _FENCE_RE.search(text)
    if fence:
        try:
            return json.loads(fence.group(1))
        except (ValueError, TypeError):
            pass
    match = _OBJECT_RE.search(text)
    if match:
        try:
            return json.loads(match.group(0))
        except (ValueError, TypeError):
            logger.warning("从 content 提取 JSON 失败", exc_info=True)
    return None


def _build_from_data(data: dict[str, Any], raw: str) -> ParsedResponse:
    """按 kind 字段把 dict 转为结构化 ParsedResponse。"""
    kind = str(data.get("kind", "")).lower()
    message = str(data.get("message") or data.get("notes") or data.get("title") or "")

    if kind == CONFIG_DRAFT:
        errors = validate_against_schema(data, CONFIG_DRAFT_SCHEMA)
        return ParsedResponse(
            kind=CONFIG_DRAFT,
            message=message,
            payload=ConfigDraft.from_dict(data) if not errors else None,
            raw=raw,
            valid=not errors,
            errors=errors,
        )
    if kind == SCRIPT_DRAFT:
        errors = validate_against_schema(data, SCRIPT_DRAFT_SCHEMA)
        return ParsedResponse(
            kind=SCRIPT_DRAFT,
            message=message,
            payload=ScriptDraft.from_dict(data) if not errors else None,
            raw=raw,
            valid=not errors,
            errors=errors,
        )
    if kind == KIND_LOG_ANALYSIS or "summary" in data and "severity" in data:
        errors = validate_against_schema(data, LOG_ANALYSIS_SCHEMA)
        return ParsedResponse(
            kind=KIND_LOG_ANALYSIS,
            message=message,
            payload=LogAnalysisResult.from_dict(data) if not errors else None,
            raw=raw,
            valid=not errors,
            errors=errors,
        )
    return ParsedResponse(kind=KIND_MESSAGE, message=message or raw, payload=None, raw=raw)


def parse(content: str, tool_calls: list[dict[str, Any]] | None = None) -> ParsedResponse:
    """解析模型输出。

    优先原生 tools；无 tool_calls 时降级到 content JSON；都不命中则按纯文本返回。
    """
    if tool_calls:
        first = tool_calls[0] or {}
        fn = first.get("function") or {}
        args = fn.get("arguments")
        data: Any = None
        if isinstance(args, str):
            try:
                data = json.loads(args)
            except (ValueError, TypeError):
                logger.warning("tool_call arguments 非合法 JSON", exc_info=True)
        elif isinstance(args, dict):
            data = args
        if isinstance(data, dict):
            data.setdefault("kind", str(fn.get("name", "")))
            return _build_from_data(data, content or "")

    data = _extract_json(content)
    if isinstance(data, dict):
        return _build_from_data(data, content or "")

    return ParsedResponse(kind=KIND_MESSAGE, message=(content or "").strip(), raw=content or "")


def parse_expected(content: str, expected_kind: str) -> ParsedResponse:
    """按调用方期望的 kind 解析（草案生成场景）。

    当模型未带 kind 字段、或带错 kind 时，注入 expected_kind 再校验，
    便于把"裸 payload"也吃进对应草案。
    """
    data = _extract_json(content)
    if not isinstance(data, dict):
        return ParsedResponse(
            kind=KIND_MESSAGE,
            message=(content or "").strip(),
            raw=content or "",
            valid=False,
            errors=["未能从输出中提取 JSON 草案"],
        )
    if str(data.get("kind", "")).lower() not in (CONFIG_DRAFT, SCRIPT_DRAFT, KIND_LOG_ANALYSIS):
        data["kind"] = expected_kind
    return _build_from_data(data, content or "")


def build_retry_hint(errors: list[str]) -> str:
    """构造给模型的纠正提示（解析/校验失败重试用）。"""
    joined = "；".join(errors) if errors else "输出格式非法"
    return (
        "上一次输出无法解析或不符合要求：" + joined + "。"
        "请严格只输出一个 JSON 对象（不要任何额外文字、不要 Markdown 代码块），"
        "并包含正确的 kind 字段与必填字段。"
    )
