"""Custom Test 序列读入兼容层。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ui.pages.custom_test.nodes import BaseNode


@dataclass(frozen=True)
class SequenceLoadResult:
    nodes: List[BaseNode]
    instruments: Dict[str, Any]
    source_format: str
    version: Optional[int] = None


def _extract_sequence_payload(data: Any) -> tuple[List[Dict[str, Any]], Dict[str, Any], str, Optional[int]]:
    if isinstance(data, dict):
        if "sequence" not in data:
            raise ValueError("序列 dict 缺少 sequence 字段")
        sequence = data["sequence"]
        instruments = data.get("instruments", {})
        if instruments is None:
            instruments = {}
        if not isinstance(instruments, dict):
            raise ValueError("instruments 字段必须是 dict")
        return sequence, instruments, "dict", data.get("version")

    if isinstance(data, list):
        return data, {}, "list", None

    raise ValueError("序列文件必须是 list 或包含 sequence 的 dict")


def load_sequence_data(data: Any) -> SequenceLoadResult:
    sequence, instruments, source_format, version = _extract_sequence_payload(data)
    if not isinstance(sequence, list):
        raise ValueError("sequence 字段必须是 list")
    nodes = [BaseNode.from_dict(item) for item in sequence]
    return SequenceLoadResult(
        nodes=nodes,
        instruments=instruments,
        source_format=source_format,
        version=version,
    )


def load_sequence_file(filepath: str) -> SequenceLoadResult:
    with open(filepath, "r", encoding="utf-8") as f:
        return load_sequence_data(json.load(f))
