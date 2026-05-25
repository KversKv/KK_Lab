from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from core.instruments.instrument_session import (
    InstrumentCandidate,
    InstrumentIdentity,
    InstrumentSpec,
)


@dataclass(frozen=True)
class InstrumentProfile:
    instrument_type: str
    display_name: str
    connection_kind: str
    role: str
    capabilities: frozenset[str]
    create: Callable[[InstrumentSpec], object]
    verify: Callable[[object], InstrumentIdentity]
    scan: Callable[[], list[InstrumentCandidate]]
    disconnect: Callable[[object], None]
    default_slot: str = "default"
