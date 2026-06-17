"""AI 结构化数据 Schema（请求/分析结果）。

阶段 2 聚焦"日志分析结果"结构化（AI_Assist.md §11）：
  - LogAnalysisResult dataclass：summary/severity/evidence/...
  - LOG_ANALYSIS_SCHEMA：对应 JSON Schema，供 response_parser（阶段 3）校验降级 JSON。

本模块纯数据，禁 import Qt。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SEVERITY_LEVELS = ("info", "low", "medium", "high", "critical")


@dataclass
class LogAnalysisResult:
    """日志分析结构化结果（与 §11 Schema 对齐）。"""

    summary: str = ""
    severity: str = "info"
    evidence: list[str] = field(default_factory=list)
    possible_causes: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    related_log_lines: list[int] = field(default_factory=list)
    confidence: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogAnalysisResult":
        severity = str(data.get("severity", "info")).lower()
        if severity not in SEVERITY_LEVELS:
            severity = "info"
        try:
            confidence = float(data.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        return cls(
            summary=str(data.get("summary", "")),
            severity=severity,
            evidence=[str(x) for x in data.get("evidence", []) or []],
            possible_causes=[str(x) for x in data.get("possible_causes", []) or []],
            suggested_actions=[str(x) for x in data.get("suggested_actions", []) or []],
            related_log_lines=[
                int(x)
                for x in (data.get("related_log_lines", []) or [])
                if str(x).lstrip("-").isdigit()
            ],
            confidence=confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "severity": self.severity,
            "evidence": list(self.evidence),
            "possible_causes": list(self.possible_causes),
            "suggested_actions": list(self.suggested_actions),
            "related_log_lines": list(self.related_log_lines),
            "confidence": self.confidence,
        }


LOG_ANALYSIS_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "severity": {"type": "string", "enum": list(SEVERITY_LEVELS)},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "possible_causes": {"type": "array", "items": {"type": "string"}},
        "suggested_actions": {"type": "array", "items": {"type": "string"}},
        "related_log_lines": {"type": "array", "items": {"type": "integer"}},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["summary", "severity"],
}
