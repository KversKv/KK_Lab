"""执行上下文：变量池 + 结果集 + 仪器句柄"""

from __future__ import annotations

import ast
import re
import operator
from typing import Any, Dict, List, Optional, Set

from log_config import get_logger

logger = get_logger(__name__)

_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "int": int,
    "float": float,
    "str": str,
    "len": len,
}


def _safe_eval_node(node: ast.AST, variables: Dict[str, Any]) -> Any:
    """受限 AST 求值器"""
    if isinstance(node, ast.Expression):
        return _safe_eval_node(node.body, variables)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in variables:
            return variables[node.id]
        if node.id in _SAFE_FUNCTIONS:
            return _SAFE_FUNCTIONS[node.id]
        raise NameError(f"未定义的变量: {node.id}")
    if isinstance(node, ast.BinOp):
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
        left = _safe_eval_node(node.left, variables)
        right = _safe_eval_node(node.right, variables)
        return op_func(left, right)
    if isinstance(node, ast.UnaryOp):
        op_func = _SAFE_OPERATORS.get(type(node.op))
        if op_func is None:
            raise ValueError(f"不支持的一元运算符: {type(node.op).__name__}")
        return op_func(_safe_eval_node(node.operand, variables))
    if isinstance(node, ast.Compare):
        left = _safe_eval_node(node.left, variables)
        for op_node, comparator in zip(node.ops, node.comparators):
            right = _safe_eval_node(comparator, variables)
            if isinstance(op_node, ast.Eq):
                result = left == right
            elif isinstance(op_node, ast.NotEq):
                result = left != right
            elif isinstance(op_node, ast.Lt):
                result = left < right
            elif isinstance(op_node, ast.LtE):
                result = left <= right
            elif isinstance(op_node, ast.Gt):
                result = left > right
            elif isinstance(op_node, ast.GtE):
                result = left >= right
            else:
                raise ValueError(f"不支持的比较运算符: {type(op_node).__name__}")
            if not result:
                return False
            left = right
        return True
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(_safe_eval_node(v, variables) for v in node.values)
        if isinstance(node.op, ast.Or):
            return any(_safe_eval_node(v, variables) for v in node.values)
    if isinstance(node, ast.IfExp):
        if _safe_eval_node(node.test, variables):
            return _safe_eval_node(node.body, variables)
        return _safe_eval_node(node.orelse, variables)
    if isinstance(node, ast.Call):
        func = _safe_eval_node(node.func, variables)
        if func not in _SAFE_FUNCTIONS.values():
            raise ValueError(f"不允许调用的函数: {func}")
        args = [_safe_eval_node(a, variables) for a in node.args]
        return func(*args)
    if isinstance(node, ast.List):
        return [_safe_eval_node(e, variables) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval_node(e, variables) for e in node.elts)
    raise ValueError(f"不支持的表达式节点: {type(node).__name__}")


_VAR_PATTERN = re.compile(r"\$\{(\w+)}")


class BreakLoop(Exception):
    pass


class ContinueLoop(Exception):
    pass


class StopExecution(Exception):
    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class TestResultException(Exception):
    def __init__(self, passed: bool, message: str = ""):
        self.passed = passed
        self.message = message
        super().__init__(message)


class ExecutionContext:
    """执行上下文：管理变量池、结果集和仪器句柄"""

    def __init__(self) -> None:
        self.variables: Dict[str, Any] = {}
        self.records: List[Dict[str, Any]] = []
        self.instruments: Dict[str, Any] = {
            "chamber": None,
            "n6705c": None,
            "scope": None,
            "freq_counter": None,
            "rf_analyzer": None,
            "i2c": None,
            "uart": None,
        }
        self._stop_requested: bool = False
        self._pause_requested: bool = False
        self._step_mode: bool = False
        self._step_event_cleared: bool = True
        self._no_export_vars: Set[str] = set()
        self._user_response: Optional[str] = None
        self._user_response_ready = False
        self._test_passed: Optional[bool] = None
        self._test_message: str = ""

        self.on_step_started: Optional[Any] = None
        self.on_step_finished: Optional[Any] = None

    def set_variable(self, name: str, value: Any, export: bool = True) -> None:
        """设置变量"""
        self.variables[name] = value
        if not export:
            self._no_export_vars.add(name)
        else:
            self._no_export_vars.discard(name)

    def is_export_var(self, name: str) -> bool:
        return name not in self._no_export_vars

    def get_variable(self, name: str, default: Any = None) -> Any:
        """获取变量"""
        return self.variables.get(name, default)

    def resolve_value(self, raw: Any) -> Any:
        """解析值：支持 ${var} 占位符和表达式求值"""
        if not isinstance(raw, str):
            return raw
        text = raw.strip()

        resolved = _VAR_PATTERN.sub(
            lambda m: str(self.variables.get(m.group(1), m.group(0))),
            text,
        )

        try:
            tree = ast.parse(resolved, mode="eval")
            return _safe_eval_node(tree, self.variables)
        except Exception:
            pass

        try:
            return ast.literal_eval(resolved)
        except Exception:
            return resolved

    def evaluate_expression(self, expr: str) -> Any:
        """对表达式进行安全求值"""
        resolved = _VAR_PATTERN.sub(
            lambda m: str(self.variables.get(m.group(1), m.group(0))),
            expr,
        )
        tree = ast.parse(resolved, mode="eval")
        return _safe_eval_node(tree, self.variables)

    def resolve_scalar(self, raw: Any) -> Any:
        value = self.resolve_value(raw)
        if isinstance(value, (list, tuple)):
            if len(value) == 1:
                return value[0]
            if len(value) == 0:
                return None
        return value

    def evaluate_condition(self, condition_expr: str) -> bool:
        saved = {}
        for k, v in self.variables.items():
            if isinstance(v, (list, tuple)) and len(v) == 1:
                saved[k] = v
                self.variables[k] = v[0]
        try:
            result = self.evaluate_expression(condition_expr)
        except Exception as e:
            logger.error("条件表达式求值失败: %s => %s", condition_expr, e)
            result = False
        finally:
            self.variables.update(saved)

        if isinstance(result, (list, tuple)):
            if len(result) == 1:
                return bool(result[0])
            return len(result) > 0
        return bool(result)

    def log_output(self, message: str) -> None:
        """输出日志到执行日志面板（可被执行器 hook）"""
        logger.info("PrintLog: %s", message)

    def record_data(self, row: Dict[str, Any]) -> None:
        """记录一行数据"""
        self.records.append(dict(row))

    def request_stop(self) -> None:
        """请求停止执行"""
        self._stop_requested = True

    def request_pause(self) -> None:
        """请求暂停"""
        self._pause_requested = True

    def request_resume(self) -> None:
        """恢复执行"""
        self._pause_requested = False

    @property
    def should_stop(self) -> bool:
        return self._stop_requested

    @property
    def should_pause(self) -> bool:
        return self._pause_requested

    def reset(self) -> None:
        """重置上下文状态"""
        self.variables.clear()
        self.records.clear()
        self._stop_requested = False
        self._pause_requested = False
        self._step_mode = False
        self._no_export_vars.clear()
        self._user_response = None
        self._user_response_ready = False
        self._test_passed = None
        self._test_message = ""
        self.on_step_started = None
        self.on_step_finished = None
