"""Custom Test sequence serialization and migration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.custom_test.nodes import BaseNode, NODE_REGISTRY
from core.custom_test.resolver import collect_required_capabilities

CURRENT_SEQUENCE_VERSION = 2


@dataclass(frozen=True)
class SequenceIssue:
    severity: str
    message: str
    node_type: str = ""
    node_uid: str = ""
    path: str = ""

    def format(self) -> str:
        location = self.path or self.node_type
        if self.node_uid:
            location = f"{location}({self.node_uid[:8]})" if location else self.node_uid[:8]
        prefix = f"[{self.severity.upper()}]"
        return f"{prefix} {location}: {self.message}" if location else f"{prefix} {self.message}"


@dataclass(frozen=True)
class SequenceDocument:
    nodes: List[BaseNode]
    instruments: Dict[str, Any]
    source_format: str
    version: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    issues: List[SequenceIssue] = field(default_factory=list)


def migrate_sequence(data: Any) -> tuple[Dict[str, Any], List[SequenceIssue]]:
    sequence, instruments, metadata, source_format, source_version = _extract_payload(data)
    issues: List[SequenceIssue] = []

    if source_version not in (None, 1, "1", "1.0", 2, "2", "2.0"):
        issues.append(SequenceIssue(
            severity="warning",
            message=f"未知序列版本 {source_version}，将按 v1/v2 兼容格式读取。",
        ))

    _collect_node_issues(sequence, issues)

    migrated_metadata = dict(metadata)
    if source_format == "list":
        migrated_metadata.setdefault("migrated_from", "legacy_list")
    elif str(source_version or "1").split(".", 1)[0] != str(CURRENT_SEQUENCE_VERSION):
        migrated_metadata.setdefault("migrated_from", f"v{source_version or 1}")

    return {
        "version": CURRENT_SEQUENCE_VERSION,
        "sequence": sequence,
        "instruments": instruments,
        "metadata": migrated_metadata,
    }, issues


def load_sequence_data(data: Any) -> SequenceDocument:
    source_version = None
    if isinstance(data, dict):
        source_version = data.get("version")
    migrated, issues = migrate_sequence(data)
    nodes: List[BaseNode] = []
    for index, node_data in enumerate(migrated["sequence"]):
        _append_node(nodes, node_data, issues, path=f"sequence[{index}]")

    metadata = dict(migrated.get("metadata", {}))
    metadata.setdefault("required_capabilities", sorted(collect_required_capabilities(nodes)))

    return SequenceDocument(
        nodes=nodes,
        instruments=dict(migrated.get("instruments", {})),
        source_format="list" if isinstance(data, list) else "dict",
        version=source_version,
        metadata=metadata,
        issues=issues,
    )


def load_sequence_file(filepath: str) -> SequenceDocument:
    with open(filepath, "r", encoding="utf-8") as f:
        return load_sequence_data(json.load(f))


def load_sequence(source: Any) -> SequenceDocument:
    if isinstance(source, str):
        return load_sequence_file(source)
    return load_sequence_data(source)


def save_sequence_data(
    nodes: List[BaseNode],
    *,
    instruments: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    meta = dict(metadata or {})
    meta["required_capabilities"] = sorted(collect_required_capabilities(nodes))
    return {
        "version": CURRENT_SEQUENCE_VERSION,
        "sequence": [node.to_dict() for node in nodes],
        "instruments": dict(instruments or {}),
        "metadata": meta,
    }


def save_sequence_file(
    filepath: str,
    nodes: List[BaseNode],
    *,
    instruments: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            save_sequence_data(nodes, instruments=instruments, metadata=metadata),
            f,
            ensure_ascii=False,
            indent=2,
        )
    return filepath


def save_sequence(
    filepath: str,
    nodes: List[BaseNode],
    *,
    instruments: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    return save_sequence_file(
        filepath,
        nodes,
        instruments=instruments,
        metadata=metadata,
    )


def _extract_payload(data: Any) -> tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any], str, Any]:
    if isinstance(data, list):
        return data, {}, {}, "list", 1
    if not isinstance(data, dict):
        raise ValueError("序列文件必须是 list 或包含 sequence 的 dict")
    if "sequence" not in data:
        raise ValueError("序列 dict 缺少 sequence 字段")

    sequence = data["sequence"]
    if not isinstance(sequence, list):
        raise ValueError("sequence 字段必须是 list")

    instruments = data.get("instruments", {})
    if instruments is None:
        instruments = {}
    if not isinstance(instruments, dict):
        raise ValueError("instruments 字段必须是 dict")

    metadata = data.get("metadata", {})
    if metadata is None:
        metadata = {}
    if not isinstance(metadata, dict):
        raise ValueError("metadata 字段必须是 dict")

    return sequence, instruments, metadata, "dict", data.get("version", 1)


def _collect_node_issues(
    sequence: List[Dict[str, Any]],
    issues: List[SequenceIssue],
    *,
    path: str = "sequence",
) -> None:
    for index, item in enumerate(sequence):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            issues.append(SequenceIssue("error", "节点必须是 dict", path=item_path))
            continue
        node_type = str(item.get("node_type", ""))
        uid = str(item.get("uid", ""))
        if not node_type:
            issues.append(SequenceIssue("error", "节点缺少 node_type", node_uid=uid, path=item_path))
            continue
        node_cls = NODE_REGISTRY.get(node_type)
        if node_cls is None:
            issues.append(SequenceIssue(
                "error",
                f"未知节点类型: {node_type}",
                node_type=node_type,
                node_uid=uid,
                path=item_path,
            ))
        else:
            params = item.get("params", {})
            if not isinstance(params, dict):
                issues.append(SequenceIssue(
                    "error",
                    "params 字段必须是 dict",
                    node_type=node_type,
                    node_uid=uid,
                    path=item_path,
                ))
                params = {}
            for schema in getattr(node_cls, "PARAM_SCHEMA", []):
                key = str(schema.get("key", ""))
                if key and key not in params:
                    issues.append(SequenceIssue(
                        "warning",
                        f"缺少参数 {key}，将使用默认值。",
                        node_type=node_type,
                        node_uid=uid,
                        path=item_path,
                    ))

        children = item.get("children", [])
        if children:
            if isinstance(children, list):
                _collect_node_issues(children, issues, path=f"{item_path}.children")
            else:
                issues.append(SequenceIssue(
                    "error",
                    "children 字段必须是 list",
                    node_type=node_type,
                    node_uid=uid,
                    path=item_path,
                ))


def _append_node(
    nodes: List[BaseNode],
    data: Any,
    issues: List[SequenceIssue],
    *,
    path: str,
) -> None:
    if not isinstance(data, dict):
        return
    node_type = str(data.get("node_type", ""))
    node_cls = NODE_REGISTRY.get(node_type)
    if node_cls is None:
        return
    try:
        kwargs = dict(data.get("params", {}))
        if data.get("uid"):
            kwargs["uid"] = data.get("uid")
        node = node_cls(**kwargs)
    except Exception as exc:
        issues.append(SequenceIssue(
            "error",
            f"节点反序列化失败: {exc}",
            node_type=node_type,
            node_uid=str(data.get("uid", "")),
            path=path,
        ))
        return
    children = data.get("children", [])
    if isinstance(children, list):
        for index, child_data in enumerate(children):
            _append_node(node.children, child_data, issues, path=f"{path}.children[{index}]")
    nodes.append(node)
