"""Breakpoint and step-run state models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Set


@dataclass
class BreakpointSet:
    node_uids: Set[str] = field(default_factory=set)

    def add(self, uid: str) -> None:
        if uid:
            self.node_uids.add(uid)

    def discard(self, uid: str) -> None:
        self.node_uids.discard(uid)

    def should_break(self, uid: str) -> bool:
        return uid in self.node_uids

    @classmethod
    def from_iterable(cls, values: Iterable[str]) -> "BreakpointSet":
        return cls(node_uids={str(value) for value in values if str(value)})


@dataclass
class StepRunState:
    enabled: bool = False
    cursor_uid: str = ""

    def stop_before(self, uid: str, breakpoints: BreakpointSet | None = None) -> bool:
        if breakpoints and breakpoints.should_break(uid):
            self.cursor_uid = uid
            return True
        if self.enabled:
            self.cursor_uid = uid
            return True
        return False

    def resume(self, *, single_step: bool = False) -> None:
        self.enabled = single_step
        self.cursor_uid = ""
