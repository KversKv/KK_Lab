from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class InstrumentSession:
    session_id: str
    instrument_type: str
    role: str
    slot: str
    connection_kind: str
    resource: str
    serial: str = ""
    model: str = ""
    display_name: str = ""
    capabilities: set[str] = field(default_factory=set)
    instance: object | None = None
    connected: bool = False
    owner: str = "manager"
    busy: bool = False
    busy_owner: str = ""
    last_error: str = ""
    updated_at: float = field(default_factory=time.time)

    def touch(self) -> None:
        self.updated_at = time.time()

    def to_snapshot(self) -> InstrumentSnapshot:
        return InstrumentSnapshot(
            session_id=self.session_id,
            instrument_type=self.instrument_type,
            role=self.role,
            slot=self.slot,
            connection_kind=self.connection_kind,
            resource=self.resource,
            serial=self.serial,
            model=self.model,
            display_name=self.display_name,
            capabilities=frozenset(self.capabilities),
            connected=self.connected,
            busy=self.busy,
            busy_owner=self.busy_owner,
            last_error=self.last_error,
            updated_at=self.updated_at,
        )


@dataclass(frozen=True)
class InstrumentSnapshot:
    session_id: str
    instrument_type: str
    role: str
    slot: str
    connection_kind: str
    resource: str
    serial: str
    model: str
    display_name: str = ""
    capabilities: frozenset[str] = field(default_factory=frozenset)
    connected: bool = False
    busy: bool = False
    busy_owner: str = ""
    last_error: str = ""
    updated_at: float = 0.0


@dataclass
class InstrumentSpec:
    instrument_type: str
    resource: str
    role: str = ""
    connection_kind: str = ""
    slot: str = "default"
    serial: str = ""
    model_hint: str = ""


@dataclass(frozen=True)
class InstrumentIdentity:
    model: str
    serial: str
    vendor: str = ""
    firmware: str = ""


@dataclass(frozen=True)
class InstrumentCandidate:
    instrument_type: str
    connection_kind: str
    resource: str
    model_hint: str = ""
    serial_hint: str = ""
    display_name: str = ""


@dataclass
class InstrumentRequirement:
    role: str = ""
    capabilities: set[str] = field(default_factory=set)
    instrument_type: str = ""
    min_count: int = 1
    max_count: int = 1
