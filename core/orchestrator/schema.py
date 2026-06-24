"""PARAM_SCHEMA validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from core.orchestrator.nodes.base import BaseNode


@dataclass(frozen=True)
class ParamIssue:
    severity: str
    key: str
    message: str


def validate_param_schema(node: BaseNode) -> List[ParamIssue]:
    issues: List[ParamIssue] = []
    params = node.params
    for schema in getattr(node, "PARAM_SCHEMA", []):
        key = str(schema.get("key", ""))
        if not key:
            continue
        required = bool(schema.get("required", True))
        if key not in params:
            if required:
                issues.append(ParamIssue("error", key, f"{key} is required."))
            continue
        value = params.get(key)
        if _is_runtime_expr(value):
            continue
        expected_type = str(schema.get("type", "str")).lower()
        coerced, ok = _coerce_for_type(value, expected_type)
        if not ok:
            issues.append(ParamIssue("error", key, f"{key} must be {expected_type}."))
            continue
        options = schema.get("options")
        if options and str(coerced) not in {str(item) for item in options}:
            issues.append(ParamIssue(
                "error",
                key,
                f"{key} must be one of: {', '.join(str(item) for item in options)}.",
            ))
        if isinstance(coerced, (int, float)) and not isinstance(coerced, bool):
            if "min" in schema and coerced < float(schema["min"]):
                issues.append(ParamIssue("error", key, f"{key} must be >= {schema['min']}."))
            if "max" in schema and coerced > float(schema["max"]):
                issues.append(ParamIssue("error", key, f"{key} must be <= {schema['max']}."))
    return issues


def _is_runtime_expr(value: Any) -> bool:
    return isinstance(value, str) and "${" in value


def _coerce_for_type(value: Any, expected_type: str) -> tuple[Any, bool]:
    if expected_type in ("", "str", "string", "text", "path"):
        return str(value) if value is not None else "", True
    if expected_type == "bool":
        if isinstance(value, bool):
            return value, True
        if isinstance(value, str):
            text = value.strip().lower()
            if text in {"true", "1", "yes", "y", "on"}:
                return True, True
            if text in {"false", "0", "no", "n", "off"}:
                return False, True
        return value, False
    if expected_type == "int":
        try:
            if isinstance(value, bool):
                return value, False
            return int(value), True
        except (TypeError, ValueError):
            return value, False
    if expected_type in ("float", "number"):
        try:
            if isinstance(value, bool):
                return value, False
            return float(value), True
        except (TypeError, ValueError):
            return value, False
    return value, True
