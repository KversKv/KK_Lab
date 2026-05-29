"""Execution event stream helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ExecutionEvent:
    type: str
    message: str = ""
    node_uid: str = ""
    node_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    payload: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(timespec="milliseconds"),
            "type": self.type,
            "message": self.message,
            "node_uid": self.node_uid,
            "node_name": self.node_name,
            "payload": dict(self.payload or {}),
        }


def append_event_jsonl(file_path: str, event: ExecutionEvent) -> None:
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event.to_dict(), ensure_ascii=False, default=str))
        f.write("\n")
