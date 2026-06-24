"""Sweep model helpers for Orchestrator."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, List


@dataclass(frozen=True)
class SweepAxis:
    name: str
    values: List[Any]


@dataclass(frozen=True)
class SweepPlan:
    axes: List[SweepAxis] = field(default_factory=list)

    @property
    def total_points(self) -> int:
        total = 1
        for axis in self.axes:
            total *= max(0, len(axis.values))
        return total if self.axes else 0

    def iter_points(self) -> Iterator[Dict[str, Any]]:
        if not self.axes:
            return
        names = [axis.name for axis in self.axes]
        values: Iterable[tuple[Any, ...]] = itertools.product(*(axis.values for axis in self.axes))
        for combo in values:
            yield dict(zip(names, combo))
