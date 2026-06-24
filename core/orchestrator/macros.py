"""Reusable sub-sequence and macro models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from core.orchestrator.nodes.base import BaseNode
from core.orchestrator.snapshot import clone_sequence, canonical_sequence_data


@dataclass
class OrchestratorMacro:
    name: str
    nodes: List[BaseNode] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)

    def instantiate(self) -> List[BaseNode]:
        return clone_sequence(self.nodes, preserve_uid=False)

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "sequence": canonical_sequence_data(self.nodes),
            "metadata": dict(self.metadata),
        }
