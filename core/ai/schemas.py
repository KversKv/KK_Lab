"""AI 结构化数据 Schema（请求/分析结果/草案）。

阶段 2 聚焦"日志分析结果"结构化（AI_Assist.md §11）：
  - LogAnalysisResult dataclass：summary/severity/evidence/...
  - LOG_ANALYSIS_SCHEMA：对应 JSON Schema，供 response_parser 校验降级 JSON。

阶段 3 新增"草案"结构化（AI_Assist.md §9 / §12）：
  - DraftKind：草案类别（测试配置 / 测试脚本-序列）。
  - ConfigDraft / ScriptDraft dataclass：AI 产出的草案载荷（仅草案，须预览 + 校验 + 确认后才能 apply）。
  - CONFIG_DRAFT_SCHEMA / SCRIPT_DRAFT_SCHEMA：对应 JSON Schema，供 response_parser 校验。

本模块纯数据，禁 import Qt。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SEVERITY_LEVELS = ("info", "low", "medium", "high", "critical")


@dataclass
class WaveformStat:
    """单通道波形统计摘要（F1 第 1 层，纯标量，不含原始点）。"""

    label: str = ""
    unit: str = ""
    sample_period_s: float = 0.0
    point_count: int = 0
    minimum: float = 0.0
    maximum: float = 0.0
    average: float = 0.0
    peak_to_peak: float = 0.0
    std: float = 0.0
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    steady_segments: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "unit": self.unit,
            "sample_period_s": self.sample_period_s,
            "point_count": self.point_count,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "average": self.average,
            "peak_to_peak": self.peak_to_peak,
            "std": self.std,
            "anomalies": list(self.anomalies),
            "steady_segments": list(self.steady_segments),
        }


@dataclass
class WaveformDigest:
    """波形摘要包（F1 三层结构的可序列化载荷）。

    stats: 各通道统计摘要（第 1 层，永远先传）；
    downsampled: LTTB 降采样后的形状数据（第 2 层，可选）：
                 {label: {"time": [...], "values": [...]}}；
    note: 给模型的说明（如"原始 150 万点已降采样至 1500 点"）。
    """

    stats: list[WaveformStat] = field(default_factory=list)
    downsampled: dict[str, dict[str, list[float]]] = field(default_factory=dict)
    note: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "stats": [s.to_dict() for s in self.stats],
            "downsampled": {
                k: {"time": list(v.get("time", [])), "values": list(v.get("values", []))}
                for k, v in self.downsampled.items()
            },
            "note": self.note,
        }


@dataclass
class TurnUsage:
    """单轮请求的用量与速度（F3，来自响应 usage + 客户端计时）。"""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    elapsed_ms: int = 0

    @property
    def output_tps(self) -> float:
        if self.elapsed_ms <= 0:
            return 0.0
        return self.completion_tokens / (self.elapsed_ms / 1000.0)

    @classmethod
    def from_result(
        cls, usage: dict[str, Any] | None, elapsed_ms: int
    ) -> "TurnUsage":
        usage = usage or {}

        def _as_int(value: Any) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0

        return cls(
            prompt_tokens=_as_int(usage.get("prompt_tokens")),
            completion_tokens=_as_int(usage.get("completion_tokens")),
            total_tokens=_as_int(usage.get("total_tokens")),
            elapsed_ms=max(0, int(elapsed_ms)),
        )


@dataclass
class SessionStats:
    """会话累计用量（F3，客户端累加）。"""

    requests: int = 0
    prompt_tokens_total: int = 0
    completion_tokens_total: int = 0

    def add(self, turn: TurnUsage) -> None:
        self.requests += 1
        self.prompt_tokens_total += turn.prompt_tokens
        self.completion_tokens_total += turn.completion_tokens

    def reset(self) -> None:
        self.requests = 0
        self.prompt_tokens_total = 0
        self.completion_tokens_total = 0


CONFIG_DRAFT = "config_draft"
SCRIPT_DRAFT = "script_draft"
DRAFT_KINDS = (CONFIG_DRAFT, SCRIPT_DRAFT)


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


@dataclass
class ConfigDraft:
    """测试配置草案（AI 产出，仅草案）。

    target_page: 草案适用的页面键（如 vmin_hunter / pmu_test），由 UI 据此选择 apply 通道；
    title/notes: 给用户看的说明；
    payload: 配置字典（结构由各页面自身的 import/校验逻辑负责）。
    """

    target_page: str = ""
    title: str = ""
    notes: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConfigDraft":
        payload = data.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        return cls(
            target_page=str(data.get("target_page", "")),
            title=str(data.get("title", "")),
            notes=str(data.get("notes", "")),
            payload=payload,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": CONFIG_DRAFT,
            "target_page": self.target_page,
            "title": self.title,
            "notes": self.notes,
            "payload": dict(self.payload),
        }


@dataclass
class ScriptDraft:
    """测试脚本（Custom Test 序列）草案（AI 产出，仅草案）。

    sequence: 节点树（list[dict]，每个含 node_type/uid?/params/children?），
              由 core/custom_test/serialization + validation 负责反序列化与 preflight；
    instruments/metadata: 可选连接 meta 与元信息。
    """

    title: str = ""
    notes: str = ""
    sequence: list[Any] = field(default_factory=list)
    instruments: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ScriptDraft":
        sequence = data.get("sequence")
        if not isinstance(sequence, list):
            sequence = []
        instruments = data.get("instruments")
        if not isinstance(instruments, dict):
            instruments = {}
        metadata = data.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        return cls(
            title=str(data.get("title", "")),
            notes=str(data.get("notes", "")),
            sequence=sequence,
            instruments=instruments,
            metadata=metadata,
        )

    def to_sequence_data(self) -> dict[str, Any]:
        """转为 core/custom_test serialization 可读的 v2 dict。"""
        return {
            "version": 2,
            "sequence": list(self.sequence),
            "instruments": dict(self.instruments),
            "metadata": dict(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": SCRIPT_DRAFT,
            "title": self.title,
            "notes": self.notes,
            "sequence": list(self.sequence),
            "instruments": dict(self.instruments),
            "metadata": dict(self.metadata),
        }


CONFIG_DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": [CONFIG_DRAFT]},
        "target_page": {"type": "string"},
        "title": {"type": "string"},
        "notes": {"type": "string"},
        "payload": {"type": "object"},
    },
    "required": ["kind", "payload"],
}


SCRIPT_DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "kind": {"type": "string", "enum": [SCRIPT_DRAFT]},
        "title": {"type": "string"},
        "notes": {"type": "string"},
        "sequence": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "node_type": {"type": "string"},
                    "uid": {"type": "string"},
                    "params": {"type": "object"},
                    "children": {"type": "array"},
                },
                "required": ["node_type"],
            },
        },
        "instruments": {"type": "object"},
        "metadata": {"type": "object"},
    },
    "required": ["kind", "sequence"],
}
