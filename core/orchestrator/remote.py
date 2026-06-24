"""Headless Orchestrator request model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

from core.orchestrator.document import OrchestratorDocument


@dataclass(frozen=True)
class HeadlessRunRequest:
    sequence_data: Any
    instrument_profile: Dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    allow_mock: bool = False

    def load_document(self) -> OrchestratorDocument:
        document = OrchestratorDocument.from_data(self.sequence_data)
        if self.instrument_profile:
            document.instruments.update(self.instrument_profile)
        return document
