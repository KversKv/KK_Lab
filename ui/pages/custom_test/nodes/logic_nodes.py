"""逻辑控制节点集合"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from log_config import get_logger
from ui.pages.custom_test.nodes.base_node import BaseNode, register_node

logger = get_logger(__name__)


@register_node
class LoopRange(BaseNode):
    """范围循环节点"""

    node_type = "LoopRange"
    display_name = "Loop (Range)"
    category = "logic"
    icon = "🔁"
    color = "#2f80ed"

    PARAM_SCHEMA = [
        {"key": "var_name", "label": "循环变量名", "type": "str", "default": "i"},
        {"key": "start", "label": "起始值", "type": "float", "default": 0.0},
        {"key": "stop", "label": "终止值", "type": "float", "default": 10.0},
        {"key": "step", "label": "步进", "type": "float", "default": 1.0},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        var_name = str(context.resolve_value(self.params["var_name"]))
        start = float(context.resolve_value(self.params["start"]))
        stop = float(context.resolve_value(self.params["stop"]))
        step_val = float(context.resolve_value(self.params["step"]))

        if step_val == 0:
            raise ValueError("步进值不能为 0")

        values: List[float] = []
        current = start
        if step_val > 0:
            while current <= stop + 1e-9:
                values.append(round(current, 10))
                current += step_val
        else:
            while current >= stop - 1e-9:
                values.append(round(current, 10))
                current += step_val

        total = len(values)
        for idx, val in enumerate(values):
            if context.should_stop:
                return
            context.set_variable(var_name, val)
            context.set_variable(f"{var_name}_index", idx)
            context.set_variable(f"{var_name}_total", total)
            logger.info("Loop %s = %s (%d/%d)", var_name, val, idx + 1, total)
            from ui.pages.custom_test.executor import _execute_children
            _execute_children(self.children, context)


@register_node
class LoopList(BaseNode):
    """列表循环节点"""

    node_type = "LoopList"
    display_name = "Loop (List)"
    category = "logic"
    icon = "🔁"
    color = "#2f80ed"

    PARAM_SCHEMA = [
        {"key": "var_name", "label": "循环变量名", "type": "str", "default": "item"},
        {"key": "values", "label": "值列表 (逗号分隔或表达式)", "type": "str",
         "default": "-20, -10, 0, 10, 25, 40, 60, 85"},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        var_name = str(context.resolve_value(self.params["var_name"]))
        raw_values = context.resolve_value(self.params["values"])

        if isinstance(raw_values, (list, tuple)):
            values = list(raw_values)
        elif isinstance(raw_values, str):
            values = [v.strip() for v in raw_values.split(",")]
            parsed = []
            for v in values:
                try:
                    parsed.append(context.evaluate_expression(v))
                except Exception:
                    parsed.append(v)
            values = parsed
        else:
            values = [raw_values]

        total = len(values)
        for idx, val in enumerate(values):
            if context.should_stop:
                return
            context.set_variable(var_name, val)
            context.set_variable(f"{var_name}_index", idx)
            context.set_variable(f"{var_name}_total", total)
            logger.info("Loop %s = %s (%d/%d)", var_name, val, idx + 1, total)
            from ui.pages.custom_test.executor import _execute_children
            _execute_children(self.children, context)


@register_node
class IfElse(BaseNode):
    """条件分支节点"""

    node_type = "IfElse"
    display_name = "If / Else"
    category = "logic"
    icon = "🔀"
    color = "#e74c3c"

    PARAM_SCHEMA = [
        {"key": "condition", "label": "条件表达式", "type": "str", "default": "${value} > 0"},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        condition = str(self.params["condition"])
        try:
            result = context.evaluate_expression(condition)
        except Exception as e:
            logger.error("条件表达式求值失败: %s => %s", condition, e)
            result = False

        logger.info("If (%s) => %s", condition, result)

        if result:
            true_children = [c for c in self.children if not getattr(c, '_is_else_branch', False)]
            from ui.pages.custom_test.executor import _execute_children
            _execute_children(true_children, context)
        else:
            false_children = [c for c in self.children if getattr(c, '_is_else_branch', False)]
            from ui.pages.custom_test.executor import _execute_children
            _execute_children(false_children, context)


@register_node
class SetVariable(BaseNode):
    """变量赋值节点"""

    node_type = "SetVariable"
    display_name = "Set Variable"
    category = "logic"
    icon = "📝"
    color = "#9b59b6"

    PARAM_SCHEMA = [
        {"key": "var_name", "label": "变量名", "type": "str", "default": "my_var"},
        {"key": "value", "label": "值（支持表达式）", "type": "str", "default": "0"},
    ]

    def execute(self, context: Any) -> None:
        var_name = str(self.params["var_name"])
        raw_value = self.params["value"]
        value = context.resolve_value(raw_value)
        context.set_variable(var_name, value)
        logger.info("SetVariable: %s = %s", var_name, value)


@register_node
class Delay(BaseNode):
    """延时节点"""

    node_type = "Delay"
    display_name = "Delay"
    category = "logic"
    icon = "⏱"
    color = "#7f8c8d"

    PARAM_SCHEMA = [
        {"key": "seconds", "label": "延时 (秒)", "type": "float", "default": 1.0},
    ]

    def execute(self, context: Any) -> None:
        seconds = float(context.resolve_value(self.params["seconds"]))
        logger.info("Delay %.2f s", seconds)
        end_time = time.time() + seconds
        while time.time() < end_time:
            if context.should_stop:
                return
            time.sleep(min(0.2, end_time - time.time()))


@register_node
class MathExpression(BaseNode):
    """数学运算节点"""

    node_type = "MathExpression"
    display_name = "Math Expression"
    category = "logic"
    icon = "🔢"
    color = "#16a085"

    PARAM_SCHEMA = [
        {"key": "expression", "label": "表达式", "type": "str", "default": "${a} + ${b}"},
        {"key": "result_var", "label": "结果变量名", "type": "str", "default": "math_result"},
    ]

    def execute(self, context: Any) -> None:
        expr = str(self.params["expression"])
        result_var = str(self.params["result_var"])
        value = context.evaluate_expression(expr)
        context.set_variable(result_var, value)
        logger.info("Math: %s = %s => %s", result_var, expr, value)
