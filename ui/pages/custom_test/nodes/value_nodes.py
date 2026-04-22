"""值/变量操作节点集合"""

from __future__ import annotations

from typing import Any, Dict, List

from log_config import get_logger
from ui.pages.custom_test.nodes.base_node import BaseNode, register_node

logger = get_logger(__name__)


@register_node
class SetConstant(BaseNode):

    node_type = "SetConstant"
    display_name = "Set Constant"
    category = "value"
    icon = "◆"
    color = "#f59e0b"

    PARAM_SCHEMA = [
        {"key": "var_name", "label": "常量名", "type": "str", "default": "PI"},
        {"key": "value", "label": "值", "type": "str", "default": "3.14159"},
        {"key": "value_type", "label": "类型", "type": "str", "default": "float",
         "options": ["int", "float", "str", "bool"]},
    ]

    def execute(self, context: Any) -> None:
        var_name = str(self.params["var_name"])
        raw_value = context.resolve_value(self.params["value"])
        value_type = str(self.params.get("value_type", "float"))

        try:
            if value_type == "int":
                raw_value = int(float(raw_value))
            elif value_type == "float":
                raw_value = float(raw_value)
            elif value_type == "bool":
                raw_value = str(raw_value).lower() in ("true", "1", "yes")
            else:
                raw_value = str(raw_value)
        except (ValueError, TypeError):
            pass

        context.set_variable(var_name, raw_value, export=False)
        logger.info("SetConstant: %s = %s (%s)", var_name, raw_value, value_type)


@register_node
class IncrementVariable(BaseNode):

    node_type = "IncrementVariable"
    display_name = "Increment (+=)"
    category = "value"
    icon = "⊕"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "var_name", "label": "变量名", "type": "str", "default": "counter"},
        {"key": "step", "label": "步进值", "type": "str", "default": "1"},
    ]

    def execute(self, context: Any) -> None:
        var_name = str(self.params["var_name"])
        step = float(context.resolve_value(self.params["step"]))
        current = context.get_variable(var_name, 0)
        try:
            current = float(current)
        except (ValueError, TypeError):
            current = 0
        new_val = current + step
        if new_val == int(new_val):
            new_val = int(new_val)
        context.set_variable(var_name, new_val)
        logger.info("Increment: %s = %s + %s = %s", var_name, current, step, new_val)


@register_node
class DecrementVariable(BaseNode):

    node_type = "DecrementVariable"
    display_name = "Decrement (-=)"
    category = "value"
    icon = "⊖"
    color = "#e74c3c"

    PARAM_SCHEMA = [
        {"key": "var_name", "label": "变量名", "type": "str", "default": "counter"},
        {"key": "step", "label": "步减值", "type": "str", "default": "1"},
    ]

    def execute(self, context: Any) -> None:
        var_name = str(self.params["var_name"])
        step = float(context.resolve_value(self.params["step"]))
        current = context.get_variable(var_name, 0)
        try:
            current = float(current)
        except (ValueError, TypeError):
            current = 0
        new_val = current - step
        if new_val == int(new_val):
            new_val = int(new_val)
        context.set_variable(var_name, new_val)
        logger.info("Decrement: %s = %s - %s = %s", var_name, current, step, new_val)


@register_node
class AppendToList(BaseNode):

    node_type = "AppendToList"
    display_name = "Append to List"
    category = "value"
    icon = "⊞"
    color = "#3498db"

    PARAM_SCHEMA = [
        {"key": "var_name", "label": "列表变量名", "type": "str", "default": "my_list"},
        {"key": "value", "label": "追加值 (支持表达式)", "type": "str", "default": "${item}"},
    ]

    def execute(self, context: Any) -> None:
        var_name = str(self.params["var_name"])
        value = context.resolve_value(self.params["value"])
        current = context.get_variable(var_name, None)
        if current is None:
            current = []
        elif not isinstance(current, list):
            current = [current]
        current.append(value)
        context.set_variable(var_name, current)
        logger.info("AppendToList: %s << %s (len=%d)", var_name, value, len(current))


@register_node
class ClearVariable(BaseNode):

    node_type = "ClearVariable"
    display_name = "Clear Variable"
    category = "value"
    icon = "⊘"
    color = "#7f8c8d"

    PARAM_SCHEMA = [
        {"key": "var_name", "label": "变量名", "type": "str", "default": "my_var"},
    ]

    def execute(self, context: Any) -> None:
        var_name = str(self.params["var_name"])
        old_val = context.get_variable(var_name)
        if var_name in context.variables:
            del context.variables[var_name]
        logger.info("ClearVariable: %s (was %s)", var_name, old_val)


@register_node
class TypeCast(BaseNode):

    node_type = "TypeCast"
    display_name = "Type Cast"
    category = "value"
    icon = "⇄"
    color = "#8e44ad"

    PARAM_SCHEMA = [
        {"key": "source_var", "label": "源变量名", "type": "str", "default": "value"},
        {"key": "target_var", "label": "目标变量名", "type": "str", "default": "value_int"},
        {"key": "cast_type", "label": "目标类型", "type": "str", "default": "int",
         "options": ["int", "float", "str", "bool"]},
    ]

    def execute(self, context: Any) -> None:
        source_var = str(self.params["source_var"])
        target_var = str(self.params["target_var"])
        cast_type = str(self.params.get("cast_type", "int"))

        raw = context.get_variable(source_var)
        if raw is None:
            raw = context.resolve_value(self.params["source_var"])

        try:
            if cast_type == "int":
                result = int(float(raw))
            elif cast_type == "float":
                result = float(raw)
            elif cast_type == "bool":
                result = str(raw).lower() in ("true", "1", "yes")
            else:
                result = str(raw)
        except (ValueError, TypeError) as e:
            logger.warning("TypeCast failed: %s -> %s (%s)", raw, cast_type, e)
            result = raw

        context.set_variable(target_var, result)
        logger.info("TypeCast: %s(%s) = %s -> %s", target_var, cast_type, raw, result)


@register_node
class ClampValue(BaseNode):

    node_type = "ClampValue"
    display_name = "Clamp Value"
    category = "value"
    icon = "⊟"
    color = "#16a085"

    PARAM_SCHEMA = [
        {"key": "var_name", "label": "变量名", "type": "str", "default": "value"},
        {"key": "min_val", "label": "最小值", "type": "str", "default": "0"},
        {"key": "max_val", "label": "最大值", "type": "str", "default": "100"},
        {"key": "result_var", "label": "结果变量名", "type": "str", "default": "clamped"},
    ]

    def execute(self, context: Any) -> None:
        var_name = str(self.params["var_name"])
        min_val = float(context.resolve_value(self.params["min_val"]))
        max_val = float(context.resolve_value(self.params["max_val"]))
        result_var = str(self.params["result_var"])

        raw = context.get_variable(var_name)
        if raw is None:
            raw = context.resolve_value(var_name)
        try:
            val = float(raw)
        except (ValueError, TypeError):
            val = 0.0

        clamped = max(min_val, min(max_val, val))
        context.set_variable(result_var, clamped)
        logger.info("Clamp: %s = clamp(%s, %s, %s) = %s", result_var, raw, min_val, max_val, clamped)
