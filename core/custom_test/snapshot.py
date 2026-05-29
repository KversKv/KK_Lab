"""Immutable-ish sequence snapshots for Custom Test runs."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any, Dict, List, Sequence

from core.custom_test.nodes.base import BaseNode
from core.custom_test.serialization import CURRENT_SEQUENCE_VERSION, save_sequence_data


def clone_node(node: BaseNode, *, preserve_uid: bool = True) -> BaseNode:
    data = copy.deepcopy(node.to_dict())
    if not preserve_uid:
        _strip_uids(data)
    return BaseNode.from_dict(data)


def clone_sequence(nodes: Sequence[BaseNode], *, preserve_uid: bool = True) -> List[BaseNode]:
    return [clone_node(node, preserve_uid=preserve_uid) for node in nodes]


def clone_sequence_with_new_ids(nodes: Sequence[BaseNode]) -> List[BaseNode]:
    return clone_sequence(nodes, preserve_uid=False)


def canonical_sequence_data(nodes: Sequence[BaseNode]) -> List[Dict[str, Any]]:
    return [copy.deepcopy(node.to_dict()) for node in nodes]


def canonical_sequence_json(nodes: Sequence[BaseNode]) -> str:
    return json.dumps(
        canonical_sequence_data(nodes),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def build_sequence_hash(nodes: Sequence[BaseNode]) -> str:
    payload = canonical_sequence_json(nodes).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_sequence_snapshot(
    file_path: str,
    nodes: Sequence[BaseNode],
    *,
    sequence_hash: str = "",
    metadata: Dict[str, Any] | None = None,
) -> str:
    meta = dict(metadata or {})
    meta["sequence_hash"] = sequence_hash or build_sequence_hash(nodes)
    data = save_sequence_data(list(nodes), metadata=meta)
    data["version"] = CURRENT_SEQUENCE_VERSION
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return file_path


def _strip_uids(data: Dict[str, Any]) -> None:
    data.pop("uid", None)
    for child in data.get("children", []) or []:
        if isinstance(child, dict):
            _strip_uids(child)
