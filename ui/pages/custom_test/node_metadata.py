"""Custom Test 节点状态与基线盘点辅助。"""

from __future__ import annotations

from typing import Any, Dict, List, Type

from ui.pages.custom_test.nodes.base_node import BaseNode

STABLE = "stable"
LEGACY = "legacy"
HIDDEN = "hidden"
UNSUPPORTED = "unsupported"
PLANNED = "planned"

_STRUCTURAL_NODE_TYPES = {
    "IfBranch",
    "ElseIfBranch",
    "ElseBranch",
}

_LEGACY_NODE_TYPES = {
    "IfElse",
    "IfThenElse",
}

_UNSUPPORTED_NODE_TYPES = {
    "PromptUser",
    "RFAnalyzerMeasure",
}

PLANNED_CAPABILITIES: Dict[str, str] = {
    "frequency_counter": "Keysight 53230A 已接入 InstrumentManager，Custom Test 节点与 adapter 后续补齐。",
}

_STATUS_NOTES: Dict[str, str] = {
    "PromptUser": "当前缺少 UI 接收端，先从 palette 隐藏；Phase 4 正规化 signal/dialog。",
    "RFAnalyzerMeasure": "CMW270/RF Analyzer 驱动未接入，先从 palette 隐藏；Phase 2/4 再进入 preflight。",
    "IfElse": "旧版条件节点，保留加载兼容但不在 palette 暴露。",
    "IfThenElse": "旧版条件节点，保留加载兼容但不在 palette 暴露。",
}

_INSTRUMENT_PREFIXES = (
    ("N6705C", "n6705c"),
    ("Scope", "scope"),
    ("Chamber", "chamber"),
    ("RFAnalyzer", "rf_analyzer"),
    ("I2C", "i2c"),
    ("MCUIO", "mcu_io"),
    ("UART", "uart"),
)

_IMPLICIT_OUTPUTS: Dict[str, List[str]] = {
    "Aggregate": ["<prefix>_avg", "<prefix>_min", "<prefix>_max", "<prefix>_sum", "<prefix>_count"],
    "ExportResult": ["_export_path", "_export_dir"],
    "I2CTraverse": ["<iter_var>_hex", "<val_var>_hex", "<iter_var>_index", "<iter_var>_total"],
    "LoopCount": ["<var_name>_index", "<var_name>_total"],
    "LoopDuration": ["<var_name>_iteration"],
    "LoopList": ["<var_name>_index", "<var_name>_total"],
    "LoopRange": ["<var_name>_index", "<var_name>_total"],
    "N6705CMeasure": ["N6705C_CH<channel>_<measure_type>"],
    "PassFailTest": ["<test_name>_result"],
    "ScopeMeasure": ["scope_CH<channel>_<measure_type>"],
    "ScopeMeasureFreq": ["scope_CH<channel>_freq"],
}

_OUTPUT_PARAM_KEYS = {
    "iter_var",
    "prefix",
    "result_var",
    "target_var",
    "val_var",
    "var_name",
}


def get_node_status(node_type: str) -> str:
    if node_type in _UNSUPPORTED_NODE_TYPES:
        return UNSUPPORTED
    if node_type in _STRUCTURAL_NODE_TYPES:
        return HIDDEN
    if node_type in _LEGACY_NODE_TYPES:
        return LEGACY
    return STABLE


def get_node_status_note(node_type: str) -> str:
    return _STATUS_NOTES.get(node_type, "")


def is_node_selectable(node_type: str) -> bool:
    return get_node_status(node_type) == STABLE


def filter_selectable_ops(ops: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [op for op in ops if is_node_selectable(str(op.get("node_type", "")))]


def get_required_instruments(node_type: str) -> List[str]:
    for prefix, instrument_id in _INSTRUMENT_PREFIXES:
        if node_type.startswith(prefix):
            return [instrument_id]
    return []


def _schema_keys(node_cls: Type[BaseNode]) -> List[str]:
    return [str(schema.get("key", "")) for schema in getattr(node_cls, "PARAM_SCHEMA", [])]


def _output_defaults(node_cls: Type[BaseNode]) -> List[str]:
    outputs: List[str] = []
    for schema in getattr(node_cls, "PARAM_SCHEMA", []):
        key = str(schema.get("key", ""))
        default = schema.get("default")
        if key in _OUTPUT_PARAM_KEYS and default not in (None, ""):
            outputs.append(str(default))
    return outputs


def build_node_inventory() -> List[Dict[str, Any]]:
    from ui.pages.custom_test.nodes import NODE_REGISTRY

    rows: List[Dict[str, Any]] = []
    for node_type, node_cls in sorted(NODE_REGISTRY.items()):
        rows.append({
            "node_type": node_type,
            "class": node_cls.__name__,
            "display_name": node_cls.display_name,
            "category": node_cls.category,
            "status": get_node_status(node_type),
            "required_instruments": get_required_instruments(node_type),
            "param_schema": _schema_keys(node_cls),
            "output_variables": _output_defaults(node_cls),
            "implicit_variables": _IMPLICIT_OUTPUTS.get(node_type, []),
            "record_data": node_type in {"RecordDataPoint", "I2CRead", "I2CTraverse", "MCUIORead", "UARTReceive"},
            "note": get_node_status_note(node_type),
        })
    return rows
