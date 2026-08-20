"""PARAM_SCHEMA validation helpers."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Any, List, Optional

from core.orchestrator.nodes.base import BaseNode


@dataclass(frozen=True)
class ParamIssue:
    severity: str
    key: str
    message: str


def validate_param_schema(
    node: BaseNode,
    known_variables: Optional[set[str]] = None,
) -> List[ParamIssue]:
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
        if _is_runtime_expr(value, known_variables):
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


def _is_runtime_expr(value: Any, known_variables: Optional[set[str]] = None) -> bool:
    if not isinstance(value, str):
        return False
    if "${" in value:
        return True
    return _references_known_variable(value, known_variables)


def _references_known_variable(
    text: str,
    known_variables: Optional[set[str]],
) -> bool:
    """裸变量名/含变量的表达式（如 "i"、"j+1"）在运行期由 resolve_value 求值。

    仅当其引用的名字都能在前序节点产生的变量（如循环变量）中找到时才放行，
    跳过静态类型/选项校验；未知名字仍按字面值参与校验，避免误放行垃圾输入。
    """
    if not known_variables:
        return False
    stripped = text.strip()
    if not stripped:
        return False
    try:
        tree = ast.parse(stripped, mode="eval")
    except (SyntaxError, ValueError):
        return False
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    return bool(names) and names <= known_variables


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
