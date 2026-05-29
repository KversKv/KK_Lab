"""Compiled execution plan model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ExecutionStep:
    uid: str
    node_type: str
    display_name: str
    path: Tuple[int, ...]
    depth: int
    required_capabilities: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionPlan:
    steps: List[ExecutionStep] = field(default_factory=list)

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def required_capabilities(self) -> Tuple[str, ...]:
        values: set[str] = set()
        for step in self.steps:
            values.update(step.required_capabilities)
        return tuple(sorted(values))

    def to_dict(self) -> Dict[str, object]:
        return {
            "total_steps": self.total_steps,
            "required_capabilities": list(self.required_capabilities),
            "steps": [
                {
                    "uid": step.uid,
                    "node_type": step.node_type,
                    "display_name": step.display_name,
                    "path": list(step.path),
                    "depth": step.depth,
                    "required_capabilities": list(step.required_capabilities),
                }
                for step in self.steps
            ],
        }
