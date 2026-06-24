"""Run artifact helpers for Orchestrator."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, Sequence

from core.orchestrator.nodes.base import BaseNode
from core.orchestrator.reports import build_html_report
from core.orchestrator.snapshot import write_sequence_snapshot


def create_run_id(timestamp: datetime | None = None) -> str:
    stamp = (timestamp or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"{stamp}_{uuid.uuid4().hex[:8]}"


@dataclass(frozen=True)
class RunArtifacts:
    run_id: str
    run_dir: str
    sequence_snapshot: str
    manifest: str
    events: str
    logs: str
    report: str


class RunHistoryWriter:
    def __init__(self, root_dir: str, *, run_id: str | None = None) -> None:
        self.run_id = run_id or create_run_id()
        self.run_dir = os.path.join(root_dir, self.run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        self.artifacts = RunArtifacts(
            run_id=self.run_id,
            run_dir=self.run_dir,
            sequence_snapshot=os.path.join(self.run_dir, "sequence_snapshot.json"),
            manifest=os.path.join(self.run_dir, "manifest.json"),
            events=os.path.join(self.run_dir, "events.jsonl"),
            logs=os.path.join(self.run_dir, "logs.txt"),
            report=os.path.join(self.run_dir, "report.html"),
        )

    def write_sequence_snapshot(
        self,
        nodes: Sequence[BaseNode],
        *,
        sequence_hash: str,
        metadata: Dict[str, Any] | None = None,
    ) -> str:
        return write_sequence_snapshot(
            self.artifacts.sequence_snapshot,
            nodes,
            sequence_hash=sequence_hash,
            metadata=metadata,
        )

    def write_manifest(self, manifest: Dict[str, Any]) -> str:
        with open(self.artifacts.manifest, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2, default=str)
        return self.artifacts.manifest

    def write_logs(self, logs: Iterable[str]) -> str:
        with open(self.artifacts.logs, "w", encoding="utf-8") as f:
            for line in logs:
                f.write(str(line))
                f.write("\n")
        return self.artifacts.logs

    def write_report(
        self,
        *,
        manifest: Dict[str, Any],
        records: Iterable[Dict[str, Any]],
        logs: Iterable[str],
    ) -> str:
        html = build_html_report(manifest=manifest, records=records, logs=logs)
        with open(self.artifacts.report, "w", encoding="utf-8") as f:
            f.write(html)
        return self.artifacts.report
