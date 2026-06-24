"""Orchestrator document model.

Version 2 sequence files remain the runtime interchange format. The v3
document wrapper keeps editor metadata, view state and dirty/source metadata
around the same sequence payload.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.orchestrator.nodes.base import BaseNode
from core.orchestrator.serialization import load_sequence_data, save_sequence_data

CURRENT_DOCUMENT_VERSION = 3


@dataclass
class OrchestratorDocument:
    nodes: List[BaseNode] = field(default_factory=list)
    instruments: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    view_state: Dict[str, Any] = field(default_factory=dict)
    source_path: Optional[str] = None
    dirty: bool = False
    version: int = CURRENT_DOCUMENT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        payload = save_sequence_data(
            self.nodes,
            instruments=self.instruments,
            metadata=self.metadata,
        )
        return {
            "version": self.version,
            "sequence": payload["sequence"],
            "instruments": payload["instruments"],
            "metadata": payload["metadata"],
            "view_state": dict(self.view_state),
        }

    @classmethod
    def from_data(cls, data: Any, *, source_path: Optional[str] = None) -> "OrchestratorDocument":
        if isinstance(data, dict) and data.get("version") == CURRENT_DOCUMENT_VERSION:
            loaded = load_sequence_data({
                "version": 2,
                "sequence": data.get("sequence", []),
                "instruments": data.get("instruments", {}),
                "metadata": data.get("metadata", {}),
            })
            return cls(
                nodes=loaded.nodes,
                instruments=loaded.instruments,
                metadata=loaded.metadata,
                view_state=dict(data.get("view_state", {}) or {}),
                source_path=source_path,
                dirty=False,
                version=CURRENT_DOCUMENT_VERSION,
            )

        loaded = load_sequence_data(data)
        metadata = dict(loaded.metadata)
        metadata.setdefault("migrated_to_document_version", CURRENT_DOCUMENT_VERSION)
        return cls(
            nodes=loaded.nodes,
            instruments=loaded.instruments,
            metadata=metadata,
            source_path=source_path,
            dirty=True,
        )


def load_document_file(file_path: str) -> OrchestratorDocument:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return OrchestratorDocument.from_data(data, source_path=file_path)


def save_document_file(file_path: str, document: OrchestratorDocument) -> str:
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(document.to_dict(), f, ensure_ascii=False, indent=2)
    document.source_path = file_path
    document.dirty = False
    return file_path
