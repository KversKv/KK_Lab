"""Custom Test 运行前校验。"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Sequence

from core.custom_test.nodes.base import BaseNode
from core.custom_test.resolver import InstrumentResolver, ResolvedInstruments

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

_VAR_REF_PATTERN = re.compile(r"\$\{(\w+)}")


@dataclass(frozen=True)
class ValidationIssue:
    severity: str
    message: str
    node_uid: str = ""
    node_type: str = ""
    fix_hint: str = ""

    def format(self) -> str:
        location = f"{self.node_type}({self.node_uid[:8]})" if self.node_uid else self.node_type
        prefix = f"[{self.severity.upper()}]"
        if location:
            return f"{prefix} {location}: {self.message}"
        return f"{prefix} {self.message}"


@dataclass
class PreflightResult:
    issues: List[ValidationIssue] = field(default_factory=list)
    resolved: Optional[ResolvedInstruments] = None

    @property
    def errors(self) -> List[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == SEVERITY_ERROR]

    @property
    def warnings(self) -> List[ValidationIssue]:
        return [issue for issue in self.issues if issue.severity == SEVERITY_WARNING]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def preflight_validate(
    nodes: Sequence[BaseNode],
    resolver: InstrumentResolver | None = None,
    sequence_version: Any = None,
) -> PreflightResult:
    result = PreflightResult()

    if sequence_version not in (None, 1, "1", "1.0"):
        result.issues.append(ValidationIssue(
            severity=SEVERITY_WARNING,
            message=f"未知序列版本: {sequence_version}",
            fix_hint="请通过当前版本重新保存序列，或检查模板迁移规则。",
        ))

    if not nodes:
        result.issues.append(ValidationIssue(
            severity=SEVERITY_ERROR,
            message="序列为空，请先添加节点。",
        ))
        return result

    produced_vars: set[str] = set()
    _validate_nodes(nodes, result.issues, produced_vars)

    if resolver is not None:
        resolved = resolver.resolve(nodes)
        result.resolved = resolved
        seen_missing: set[tuple[str, tuple[str, ...], str]] = set()
        for missing in resolved.missing:
            key = (missing.runtime_key, missing.capabilities, missing.source)
            if key in seen_missing:
                continue
            seen_missing.add(key)
            severity = SEVERITY_ERROR
            result.issues.append(ValidationIssue(
                severity=severity,
                message=missing.message,
                fix_hint=_instrument_fix_hint(missing.runtime_key, missing.source),
            ))
        for warning in resolved.warnings:
            result.issues.append(ValidationIssue(
                severity=SEVERITY_WARNING,
                message=warning,
            ))

    return result


def _validate_nodes(
    nodes: Iterable[BaseNode],
    issues: List[ValidationIssue],
    produced_vars: set[str],
) -> None:
    for node in nodes:
        unsupported = getattr(node, "unsupported_reason", "")
        if unsupported:
            issues.append(ValidationIssue(
                severity=SEVERITY_ERROR,
                node_uid=node.uid,
                node_type=node.node_type,
                message=unsupported,
                fix_hint="请删除/替换该节点，或等待对应能力接入。",
            ))

        _validate_params(node, issues, produced_vars)
        child_produced = set(produced_vars)
        _register_outputs_before_children(node, child_produced)
        if node.children:
            _validate_nodes(node.children, issues, child_produced)
        produced_vars.update(child_produced)
        _register_node_outputs(node, produced_vars)


def _validate_params(
    node: BaseNode,
    issues: List[ValidationIssue],
    produced_vars: set[str],
) -> None:
    params = node.params
    nt = node.node_type

    if nt == "LoopRange":
        _require_non_empty(node, "var_name", issues)
        _require_non_zero_number(node, "step", issues, "LoopRange step 不能为 0。")
    elif nt == "LoopCount":
        _require_non_empty(node, "var_name", issues)
        _require_number_at_least(node, "count", 0, issues, "LoopCount count 不能为负数。")
    elif nt in {"WhileLoop", "RepeatUntil"}:
        _require_number_at_least(node, "max_iterations", 1, issues, "最大迭代次数至少为 1。")
    elif nt == "LoopDuration":
        _require_number_at_least(node, "duration", 0, issues, "LoopDuration duration 不能为负数。")
    elif nt == "Delay":
        _require_number_at_least(node, "seconds", 0, issues, "Delay seconds 不能为负数。")
    elif nt == "WaitUntil":
        _require_number_at_least(node, "timeout", 0, issues, "WaitUntil timeout 不能为负数。")
        _require_number_at_least(node, "poll_interval", 0.001, issues, "WaitUntil poll_interval 必须大于 0。")
    elif nt == "ChamberSetTemp":
        _require_number_at_least(node, "stable_time", 0, issues, "stable_time 不能为负数。")
    elif nt == "ChamberWaitStable":
        _require_number_at_least(node, "poll_interval", 0.001, issues, "poll_interval 必须大于 0。")
        _require_number_at_least(node, "window_seconds", 0, issues, "window_seconds 不能为负数。")
        _require_number_at_least(node, "stable_hits", 1, issues, "stable_hits 至少为 1。")
        _require_number_at_least(node, "max_wait_s", 0, issues, "max_wait_s 不能为负数。")
    elif nt == "MCUIOPulse":
        _require_number_at_least(node, "duration_s", 0, issues, "Pulse duration 不能为负数。")
    elif nt == "UARTReceive":
        _require_number_at_least(node, "timeout_s", 0, issues, "UART timeout 不能为负数。")

    for key, value in params.items():
        if key == "result_var":
            _require_non_empty(node, key, issues)
        if key in {"condition", "expression"} and isinstance(value, str):
            _validate_expression_syntax(node, key, value, issues)
        if isinstance(value, str):
            _warn_unknown_variable_refs(node, key, value, issues, produced_vars)


def _register_outputs_before_children(node: BaseNode, produced_vars: set[str]) -> None:
    if node.node_type in {"LoopRange", "LoopList", "LoopCount"}:
        var_name = str(node.params.get("var_name", "")).strip()
        if var_name:
            produced_vars.update({var_name, f"{var_name}_index", f"{var_name}_total"})
    elif node.node_type == "LoopDuration":
        var_name = str(node.params.get("var_name", "")).strip()
        if var_name:
            produced_vars.update({var_name, f"{var_name}_iteration"})
    elif node.node_type == "I2CTraverse":
        iter_var = str(node.params.get("iter_var", "reg")).strip()
        val_var = str(node.params.get("val_var", "reg_val")).strip()
        if iter_var:
            produced_vars.update({iter_var, f"{iter_var}_hex", f"{iter_var}_index", f"{iter_var}_total"})
        if val_var:
            produced_vars.update({val_var, f"{val_var}_hex"})


def _register_node_outputs(node: BaseNode, produced_vars: set[str]) -> None:
    for key in ("var_name", "result_var", "target_var"):
        value = str(node.params.get(key, "")).strip()
        if value:
            produced_vars.add(value)

    if node.node_type == "N6705CMeasure":
        ch = node.params.get("channel", 1)
        measure_type = node.params.get("measure_type", "current")
        produced_vars.add(f"N6705C_CH{ch}_{measure_type}")
    elif node.node_type == "ScopeMeasure":
        ch = node.params.get("channel", 1)
        measure_type = node.params.get("measure_type", "pk2pk")
        produced_vars.add(f"scope_CH{ch}_{measure_type}")
    elif node.node_type == "ScopeMeasureFreq":
        ch = node.params.get("channel", 1)
        produced_vars.add(f"scope_CH{ch}_freq")
    elif node.node_type == "Aggregate":
        prefix = str(node.params.get("prefix", "stat")).strip()
        if prefix:
            produced_vars.update({
                f"{prefix}_avg", f"{prefix}_min", f"{prefix}_max",
                f"{prefix}_sum", f"{prefix}_count",
            })


def _require_non_empty(
    node: BaseNode,
    key: str,
    issues: List[ValidationIssue],
) -> None:
    if str(node.params.get(key, "")).strip():
        return
    issues.append(ValidationIssue(
        severity=SEVERITY_ERROR,
        node_uid=node.uid,
        node_type=node.node_type,
        message=f"{key} 不能为空。",
    ))


def _require_non_zero_number(
    node: BaseNode,
    key: str,
    issues: List[ValidationIssue],
    message: str,
) -> None:
    value = _literal_number(node.params.get(key))
    if value is None or value != 0:
        return
    issues.append(ValidationIssue(
        severity=SEVERITY_ERROR,
        node_uid=node.uid,
        node_type=node.node_type,
        message=message,
    ))


def _require_number_at_least(
    node: BaseNode,
    key: str,
    minimum: float,
    issues: List[ValidationIssue],
    message: str,
) -> None:
    value = _literal_number(node.params.get(key))
    if value is None or value >= minimum:
        return
    issues.append(ValidationIssue(
        severity=SEVERITY_ERROR,
        node_uid=node.uid,
        node_type=node.node_type,
        message=message,
    ))


def _literal_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if "${" in text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _validate_expression_syntax(
    node: BaseNode,
    key: str,
    expression: str,
    issues: List[ValidationIssue],
) -> None:
    normalized = _VAR_REF_PATTERN.sub("1", expression)
    try:
        ast.parse(normalized, mode="eval")
    except SyntaxError as exc:
        issues.append(ValidationIssue(
            severity=SEVERITY_ERROR,
            node_uid=node.uid,
            node_type=node.node_type,
            message=f"{key} 表达式语法错误: {exc.msg}",
        ))


def _warn_unknown_variable_refs(
    node: BaseNode,
    key: str,
    text: str,
    issues: List[ValidationIssue],
    produced_vars: set[str],
) -> None:
    for var_name in _VAR_REF_PATTERN.findall(text):
        if var_name not in produced_vars:
            issues.append(ValidationIssue(
                severity=SEVERITY_WARNING,
                node_uid=node.uid,
                node_type=node.node_type,
                message=f"{key} 引用了尚未在前序节点中产生的变量: {var_name}",
                fix_hint="如果该变量来自运行期外部注入，可忽略此警告。",
            ))


def _instrument_fix_hint(runtime_key: str, source: str) -> str:
    if source == "busy":
        return "等待其它页面释放该仪器，或停止占用该 session 的任务。"
    if source == "unsupported":
        return "请删除该节点或先接入对应仪器驱动/adapter。"
    labels = {
        "n6705c": "请连接 N6705C Power Analyzer。",
        "scope": "请连接 MSO64B/DSOX4034A 示波器。",
        "chamber": "请连接温箱。",
        "i2c": "请连接 BES USB-I2C 或确认 DLL 可用。",
        "uart": "请连接 UART 串口。",
        "mcu_io": "请连接 MCU IO 控制器。",
    }
    return labels.get(runtime_key, "请在 InstrumentManager 中连接所需仪器。")
