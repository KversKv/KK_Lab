"""逻辑控制节点集合"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from log_config import get_logger
from ui.pages.custom_test.nodes.base_node import BaseNode, register_node
from ui.pages.custom_test.context import (
    BreakLoop, ContinueLoop, StopExecution, TestResultException,
)

logger = get_logger(__name__)


@register_node
class LoopRange(BaseNode):
    """范围循环节点"""

    node_type = "LoopRange"
    display_name = "Loop (Range)"
    category = "logic"
    icon = "↻"
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
            try:
                from ui.pages.custom_test.executor import _execute_children
                _execute_children(self.children, context)
            except BreakLoop:
                logger.info("Loop %s: break at iteration %d", var_name, idx)
                return


@register_node
class LoopList(BaseNode):
    """列表循环节点"""

    node_type = "LoopList"
    display_name = "Loop (List)"
    category = "logic"
    icon = "↻"
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
            try:
                from ui.pages.custom_test.executor import _execute_children
                _execute_children(self.children, context)
            except BreakLoop:
                logger.info("Loop %s: break at iteration %d", var_name, idx)
                return


@register_node
class IfBranch(BaseNode):

    node_type = "IfBranch"
    display_name = "If"
    category = "logic"
    icon = "⋔"
    color = "#e74c3c"

    PARAM_SCHEMA = [
        {"key": "condition", "label": "条件表达式", "type": "str", "default": "${value} > 0"},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        pass


@register_node
class ElseIfBranch(BaseNode):

    node_type = "ElseIfBranch"
    display_name = "Else If"
    category = "logic"
    icon = "⋔"
    color = "#e67e22"

    PARAM_SCHEMA = [
        {"key": "condition", "label": "条件表达式", "type": "str", "default": "${value} > 0"},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        pass


@register_node
class ElseBranch(BaseNode):

    node_type = "ElseBranch"
    display_name = "Else"
    category = "logic"
    icon = "⋔"
    color = "#7f8c8d"

    PARAM_SCHEMA: List[Dict[str, Any]] = []

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        pass


@register_node
class IfBlock(BaseNode):

    node_type = "IfBlock"
    display_name = "If / Else"
    category = "logic"
    icon = "⋔"
    color = "#e74c3c"

    PARAM_SCHEMA: List[Dict[str, Any]] = []

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        from ui.pages.custom_test.executor import _execute_children

        for child in self.children:
            if isinstance(child, IfBranch) or isinstance(child, ElseIfBranch):
                condition = str(child.params.get("condition", "True"))
                result = context.evaluate_condition(condition)
                logger.info("%s (%s) => %s", child.display_name, condition, result)
                if result:
                    _execute_children(child.children, context)
                    return
            elif isinstance(child, ElseBranch):
                logger.info("Else branch triggered")
                _execute_children(child.children, context)
                return
            else:
                pass

    def ensure_structure(self) -> None:
        has_if = any(isinstance(c, IfBranch) for c in self.children)
        has_else = any(isinstance(c, ElseBranch) for c in self.children)
        if not has_if:
            self.children.insert(0, IfBranch(uid=None))
            self.children[0].params["condition"] = "${value} > 0"
        if not has_else:
            self.children.append(ElseBranch(uid=None))


@register_node
class IfElse(BaseNode):
    """条件分支节点 (旧版，兼容已有模板)"""

    node_type = "IfElse"
    display_name = "If / Else (Legacy)"
    category = "logic"
    icon = "⋔"
    color = "#e74c3c"

    PARAM_SCHEMA = [
        {"key": "condition", "label": "条件表达式", "type": "str", "default": "${value} > 0"},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        condition = str(self.params["condition"])
        result = context.evaluate_condition(condition)
        logger.info("If (%s) => %s", condition, result)

        from ui.pages.custom_test.executor import _execute_children
        if result:
            _execute_children(self.children, context)
        else:
            pass


@register_node
class SetVariable(BaseNode):

    node_type = "SetVariable"
    display_name = "Set Variable"
    category = "logic"
    icon = "≔"
    color = "#9b59b6"

    PARAM_SCHEMA = [
        {"key": "var_name", "label": "变量名", "type": "str", "default": "my_var"},
        {"key": "value", "label": "值（支持表达式）", "type": "str", "default": "0"},
        {"key": "export_var", "label": "导出变量到记录", "type": "bool", "default": True},
    ]

    def execute(self, context: Any) -> None:
        var_name = str(self.params["var_name"])
        raw_value = self.params["value"]
        export_var = bool(context.resolve_value(self.params.get("export_var", True)))
        value = context.resolve_value(raw_value)
        context.set_variable(var_name, value, export=export_var)
        logger.info("SetVariable: %s = %s (export=%s)", var_name, value, export_var)


@register_node
class Delay(BaseNode):
    """延时节点"""

    node_type = "Delay"
    display_name = "Delay"
    category = "logic"
    icon = "◷"
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
    icon = "Σ"
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


@register_node
class BreakNode(BaseNode):

    node_type = "Break"
    display_name = "Break"
    category = "logic"
    icon = "⊘"
    color = "#e74c3c"

    PARAM_SCHEMA: List[Dict[str, Any]] = []

    def execute(self, context: Any) -> None:
        logger.info("Break: 跳出当前循环")
        raise BreakLoop()


@register_node
class ContinueNode(BaseNode):

    node_type = "Continue"
    display_name = "Continue"
    category = "logic"
    icon = "⇥"
    color = "#e67e22"

    PARAM_SCHEMA: List[Dict[str, Any]] = []

    def execute(self, context: Any) -> None:
        logger.info("Continue: 跳过本次迭代")
        raise ContinueLoop()


@register_node
class WaitUntil(BaseNode):

    node_type = "WaitUntil"
    display_name = "Wait Until"
    category = "logic"
    icon = "◴"
    color = "#7f8c8d"

    PARAM_SCHEMA = [
        {"key": "condition", "label": "等待条件表达式", "type": "str",
         "default": "${voltage} > 3.0"},
        {"key": "timeout", "label": "超时 (秒)", "type": "float", "default": 60.0},
        {"key": "poll_interval", "label": "轮询间隔 (秒)", "type": "float", "default": 1.0},
        {"key": "timeout_action", "label": "超时动作", "type": "str", "default": "warn",
         "options": ["warn", "error", "break"]},
    ]

    def execute(self, context: Any) -> None:
        condition = str(self.params["condition"])
        timeout = float(context.resolve_value(self.params["timeout"]))
        poll = float(context.resolve_value(self.params["poll_interval"]))
        timeout_action = str(context.resolve_value(self.params["timeout_action"]))

        logger.info("WaitUntil: %s (timeout=%ss)", condition, timeout)
        deadline = time.time() + timeout

        while time.time() < deadline:
            if context.should_stop:
                return
            if context.evaluate_condition(condition):
                logger.info("WaitUntil: 条件满足")
                return
            time.sleep(min(poll, deadline - time.time()))

        msg = f"WaitUntil 超时: {condition}"
        if timeout_action == "error":
            raise RuntimeError(msg)
        elif timeout_action == "break":
            logger.warning(msg)
            raise BreakLoop()
        else:
            logger.warning(msg)


@register_node
class IfThenStop(BaseNode):

    node_type = "IfThenStop"
    display_name = "If Then Stop"
    category = "logic"
    icon = "⊗"
    color = "#e74c3c"

    PARAM_SCHEMA = [
        {"key": "condition", "label": "条件表达式", "type": "str",
         "default": "${error_count} > 0"},
        {"key": "message", "label": "停止消息", "type": "str", "default": "条件触发，执行已停止"},
    ]

    def execute(self, context: Any) -> None:
        condition = str(self.params["condition"])
        message = str(context.resolve_value(self.params["message"]))

        result = context.evaluate_condition(condition)
        logger.info("IfThenStop (%s) => %s", condition, result)

        if result:
            raise StopExecution(message)


@register_node
class IfThenElse(BaseNode):

    node_type = "IfThenElse"
    display_name = "If / Then / Else (Legacy)"
    category = "logic"
    icon = "⋔"
    color = "#e74c3c"

    PARAM_SCHEMA = [
        {"key": "condition", "label": "条件表达式", "type": "str",
         "default": "${value} > 0"},
        {"key": "else_index", "label": "Else 分支起始索引 (从0开始)", "type": "int",
         "default": 1},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        condition = str(self.params["condition"])
        else_idx = int(context.resolve_value(self.params["else_index"]))
        result = context.evaluate_condition(condition)
        logger.info("IfThenElse (%s) => %s", condition, result)

        from ui.pages.custom_test.executor import _execute_children
        if result:
            _execute_children(self.children[:else_idx], context)
        else:
            _execute_children(self.children[else_idx:], context)


@register_node
class PromptUser(BaseNode):

    node_type = "PromptUser"
    display_name = "Prompt / Ask User"
    category = "logic"
    icon = "⊙"
    color = "#3498db"

    PARAM_SCHEMA = [
        {"key": "message", "label": "提示消息", "type": "str",
         "default": "请确认设备状态后继续"},
        {"key": "wait_confirm", "label": "等待用户确认", "type": "bool", "default": True},
        {"key": "result_var", "label": "结果存入变量 (可选)", "type": "str", "default": ""},
    ]

    def execute(self, context: Any) -> None:
        message = str(context.resolve_value(self.params["message"]))
        wait_confirm = context.resolve_value(self.params["wait_confirm"])
        result_var = str(self.params["result_var"]).strip()

        logger.info("PromptUser: %s", message)

        if wait_confirm:
            context._user_response_ready = False
            context._user_response = None

            from PySide6.QtCore import QMetaObject, Qt as QtConst, Q_ARG
            from PySide6.QtWidgets import QApplication, QMessageBox

            app = QApplication.instance()
            if app is not None:
                QMetaObject.invokeMethod(
                    app, "_custom_test_prompt",
                    QtConst.QueuedConnection,
                    Q_ARG(str, message),
                )

            timeout = 300
            deadline = time.time() + timeout
            while not context._user_response_ready:
                if context.should_stop:
                    return
                if time.time() > deadline:
                    logger.warning("PromptUser: 等待用户响应超时")
                    break
                time.sleep(0.2)

            if result_var:
                context.set_variable(result_var, context._user_response or "confirmed")


@register_node
class PassFailTest(BaseNode):

    node_type = "PassFailTest"
    display_name = "Pass/Fail Test"
    category = "logic"
    icon = "◈"
    color = "#27ae60"

    PARAM_SCHEMA = [
        {"key": "condition", "label": "通过条件", "type": "str",
         "default": "${value} >= ${min_spec} and ${value} <= ${max_spec}"},
        {"key": "test_name", "label": "测试名称", "type": "str", "default": "Test"},
        {"key": "on_fail", "label": "失败动作", "type": "str", "default": "continue",
         "options": ["continue", "stop", "break"]},
    ]

    def execute(self, context: Any) -> None:
        condition = str(self.params["condition"])
        test_name = str(context.resolve_value(self.params["test_name"]))
        on_fail = str(context.resolve_value(self.params["on_fail"]))

        passed = context.evaluate_condition(condition)

        context.set_variable(f"{test_name}_result", "PASS" if passed else "FAIL")
        logger.info("PassFail [%s] (%s) => %s", test_name, condition, "PASS" if passed else "FAIL")

        if not passed:
            if on_fail == "stop":
                raise TestResultException(False, f"{test_name}: FAIL ({condition})")
            elif on_fail == "break":
                raise BreakLoop()


@register_node
class Group(BaseNode):

    node_type = "Group"
    display_name = "Group"
    category = "logic"
    icon = "▣"
    color = "#8e44ad"

    PARAM_SCHEMA = [
        {"key": "label", "label": "分组标签", "type": "str", "default": "Group"},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        label = str(context.resolve_value(self.params["label"]))
        logger.info("Group [%s] — %d children", label, len(self.children))
        from ui.pages.custom_test.executor import _execute_children
        _execute_children(self.children, context)


@register_node
class LoopCount(BaseNode):

    node_type = "LoopCount"
    display_name = "Loop (Count)"
    category = "logic"
    icon = "↻"
    color = "#2f80ed"

    PARAM_SCHEMA = [
        {"key": "count", "label": "循环次数", "type": "int", "default": 10},
        {"key": "var_name", "label": "计数变量名", "type": "str", "default": "n"},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        count = int(context.resolve_value(self.params["count"]))
        var_name = str(context.resolve_value(self.params["var_name"]))

        for idx in range(count):
            if context.should_stop:
                return
            context.set_variable(var_name, idx)
            context.set_variable(f"{var_name}_index", idx)
            context.set_variable(f"{var_name}_total", count)
            logger.info("LoopCount %s = %d (%d/%d)", var_name, idx, idx + 1, count)
            try:
                from ui.pages.custom_test.executor import _execute_children
                _execute_children(self.children, context)
            except BreakLoop:
                logger.info("LoopCount %s: break at iteration %d", var_name, idx)
                return


@register_node
class LoopDuration(BaseNode):

    node_type = "LoopDuration"
    display_name = "Loop (Duration)"
    category = "logic"
    icon = "↻"
    color = "#2f80ed"

    PARAM_SCHEMA = [
        {"key": "duration", "label": "持续时间 (秒)", "type": "float", "default": 60.0},
        {"key": "var_name", "label": "计数变量名", "type": "str", "default": "elapsed"},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        duration = float(context.resolve_value(self.params["duration"]))
        var_name = str(context.resolve_value(self.params["var_name"]))

        start_time = time.time()
        iteration = 0
        while True:
            elapsed = time.time() - start_time
            if elapsed >= duration or context.should_stop:
                break
            context.set_variable(var_name, round(elapsed, 3))
            context.set_variable(f"{var_name}_iteration", iteration)
            logger.info("LoopDuration %s = %.1fs (iter=%d)", var_name, elapsed, iteration)
            try:
                from ui.pages.custom_test.executor import _execute_children
                _execute_children(self.children, context)
            except BreakLoop:
                logger.info("LoopDuration %s: break at %.1fs", var_name, elapsed)
                return
            iteration += 1

        context.set_variable(var_name, round(time.time() - start_time, 3))


@register_node
class WhileLoop(BaseNode):

    node_type = "WhileLoop"
    display_name = "While (Condition)"
    category = "logic"
    icon = "↻"
    color = "#2f80ed"

    PARAM_SCHEMA = [
        {"key": "condition", "label": "循环条件", "type": "str",
         "default": "${counter} < 100"},
        {"key": "max_iterations", "label": "最大迭代次数 (安全限制)", "type": "int",
         "default": 10000},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        condition = str(self.params["condition"])
        max_iter = int(context.resolve_value(self.params["max_iterations"]))

        iteration = 0
        while context.evaluate_condition(condition):
            if context.should_stop or iteration >= max_iter:
                if iteration >= max_iter:
                    logger.warning("WhileLoop: 达到最大迭代次数 %d", max_iter)
                break
            logger.info("WhileLoop iter=%d (%s)", iteration, condition)
            try:
                from ui.pages.custom_test.executor import _execute_children
                _execute_children(self.children, context)
            except BreakLoop:
                logger.info("WhileLoop: break at iteration %d", iteration)
                return
            iteration += 1


@register_node
class RepeatUntil(BaseNode):

    node_type = "RepeatUntil"
    display_name = "Repeat Until"
    category = "logic"
    icon = "↻"
    color = "#2f80ed"

    PARAM_SCHEMA = [
        {"key": "condition", "label": "退出条件 (为真时停止)", "type": "str",
         "default": "${done} == 1"},
        {"key": "max_iterations", "label": "最大迭代次数 (安全限制)", "type": "int",
         "default": 10000},
    ]

    @property
    def accepts_children(self) -> bool:
        return True

    def execute(self, context: Any) -> None:
        condition = str(self.params["condition"])
        max_iter = int(context.resolve_value(self.params["max_iterations"]))

        iteration = 0
        while True:
            if context.should_stop or iteration >= max_iter:
                if iteration >= max_iter:
                    logger.warning("RepeatUntil: 达到最大迭代次数 %d", max_iter)
                break
            logger.info("RepeatUntil iter=%d, exit when (%s)", iteration, condition)
            try:
                from ui.pages.custom_test.executor import _execute_children
                _execute_children(self.children, context)
            except BreakLoop:
                logger.info("RepeatUntil: break at iteration %d", iteration)
                return
            iteration += 1

            if context.evaluate_condition(condition):
                logger.info("RepeatUntil: 退出条件满足 (%s)", condition)
                return
