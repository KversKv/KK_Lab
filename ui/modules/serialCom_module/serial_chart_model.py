import time
import uuid
from dataclasses import dataclass, field

from log_config import get_logger

logger = get_logger(__name__)


CHART_MAX_POINTS_DEFAULT = 5000
CHART_LINE_MAX_LEN = 4096
CHART_FRAME_MAX_LINES = 64
CHART_FRAME_MAX_BYTES = 64 * 1024
CHART_FRAME_TIMEOUT_MS = 5000
CHART_REFRESH_INTERVAL_MS = 150
CHART_RULE_WARN_COUNT = 50

FIELD_TYPES = ("int", "float", "bool", "pass_fail", "enum", "string")
MATCH_MODES = ("contains", "prefix_suffix", "regex", "frame", "custom_enum")
INPUT_MODES = ("line", "bytes_hex", "bytes_raw")
EMIT_POLICIES = ("each_match", "first_match", "last_match_per_line")
TIMESTAMP_MODES = ("rx_time", "sequence_index")
CHART_TYPES = ("line", "scatter", "step")
GROUP_BY_OPTIONS = ("none", "channel", "key", "session")
SOURCE_SESSIONS = ("active", "all")

DERIVED_OPERATIONS = (
    "add", "subtract", "multiply", "divide", "rolling_avg", "rolling_rate",
)

PASS_FAIL_DEFAULT_MAP = {
    "PASS": 1, "OK": 1, "SUCCESS": 1, "TRUE": 1, "1": 1, "GOOD": 1,
    "FAIL": 0, "NG": 0, "ERROR": 0, "FALSE": 0, "0": 0, "BAD": 0,
}

DEFAULT_COLORS = (
    "#15d1a3", "#ffb84d", "#5b9bff", "#ff6b9d", "#c084fc",
    "#facc15", "#34d399", "#f87171", "#60a5fa", "#fb923c",
)

PRESET_TEMPLATES = {
    "KEY=FLOAT": r"(?P<key>[A-Za-z_][\w-]*)\s*[=:]\s*(?P<value>[+-]?\d+(?:\.\d+)?)",
    "CHx KEY=FLOAT": r"CH(?P<channel>\d+)\s+(?P<key>[A-Za-z_][\w-]*)[=:](?P<value>[+-]?\d+(?:\.\d+)?)",
    "PASS/FAIL": r"(?P<result>PASS|FAIL|OK|NG)",
    "ENUM STATE": r"STATE[=:]\s*(?P<state>[A-Za-z_][\w-]*)",
    "XML-LIKE TAG": r"<(?P<key>\w+)>(?P<value>.*?)</(?P=key)>",
}


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@dataclass
class FieldSpec:
    name: str = ""
    type: str = "float"
    unit: str = ""
    group: str = ""
    enum_map: dict = field(default_factory=dict)
    pass_fail_map: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "type": self.type,
            "unit": self.unit,
            "group": self.group,
            "enum_map": dict(self.enum_map),
            "pass_fail_map": dict(self.pass_fail_map),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FieldSpec":
        if not isinstance(data, dict):
            return cls()
        return cls(
            name=str(data.get("name", "")),
            type=str(data.get("type", "float")),
            unit=str(data.get("unit", "")),
            group=str(data.get("group", "")),
            enum_map=dict(data.get("enum_map") or {}),
            pass_fail_map=dict(data.get("pass_fail_map") or {}),
        )


@dataclass
class ChartRule:
    rule_id: str = field(default_factory=lambda: new_id("rule"))
    name: str = "New Rule"
    enabled: bool = True
    source_session: str = "active"
    input_mode: str = "line"
    match_mode: str = "regex"
    keyword_before: str = ""
    keyword_after: str = ""
    regex: str = ""
    case_sensitive: bool = False
    field_specs: list = field(default_factory=list)
    emit_policy: str = "each_match"
    timestamp_mode: str = "rx_time"
    frame_start: str = ""
    frame_end: str = ""

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "enabled": self.enabled,
            "source_session": self.source_session,
            "input_mode": self.input_mode,
            "match_mode": self.match_mode,
            "keyword_before": self.keyword_before,
            "keyword_after": self.keyword_after,
            "regex": self.regex,
            "case_sensitive": self.case_sensitive,
            "field_specs": [f.to_dict() for f in self.field_specs],
            "emit_policy": self.emit_policy,
            "timestamp_mode": self.timestamp_mode,
            "frame_start": self.frame_start,
            "frame_end": self.frame_end,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChartRule":
        if not isinstance(data, dict):
            return cls()
        specs = [FieldSpec.from_dict(s) for s in (data.get("field_specs") or [])]
        return cls(
            rule_id=str(data.get("rule_id") or new_id("rule")),
            name=str(data.get("name", "Rule")),
            enabled=bool(data.get("enabled", True)),
            source_session=str(data.get("source_session", "active")),
            input_mode=str(data.get("input_mode", "line")),
            match_mode=str(data.get("match_mode", "regex")),
            keyword_before=str(data.get("keyword_before", "")),
            keyword_after=str(data.get("keyword_after", "")),
            regex=str(data.get("regex", "")),
            case_sensitive=bool(data.get("case_sensitive", False)),
            field_specs=specs,
            emit_policy=str(data.get("emit_policy", "each_match")),
            timestamp_mode=str(data.get("timestamp_mode", "rx_time")),
            frame_start=str(data.get("frame_start", "")),
            frame_end=str(data.get("frame_end", "")),
        )


@dataclass
class ChartSeries:
    series_id: str = field(default_factory=lambda: new_id("series"))
    name: str = "New Series"
    enabled: bool = True
    source_type: str = "field"
    rule_id: str = ""
    field_name: str = ""
    group_by: str = "none"
    chart_type: str = "line"
    axis: str = "left"
    color: str = "#15d1a3"
    max_points: int = CHART_MAX_POINTS_DEFAULT
    time_window_s: float = 0.0
    operation: str = "add"
    source_a: str = ""
    source_b: str = ""
    op_window: int = 100
    op_value: float = 1.0
    op_scale: float = 1.0

    def to_dict(self) -> dict:
        return {
            "series_id": self.series_id,
            "name": self.name,
            "enabled": self.enabled,
            "source_type": self.source_type,
            "rule_id": self.rule_id,
            "field_name": self.field_name,
            "group_by": self.group_by,
            "chart_type": self.chart_type,
            "axis": self.axis,
            "color": self.color,
            "max_points": self.max_points,
            "time_window_s": self.time_window_s,
            "operation": self.operation,
            "source_a": self.source_a,
            "source_b": self.source_b,
            "op_window": self.op_window,
            "op_value": self.op_value,
            "op_scale": self.op_scale,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChartSeries":
        if not isinstance(data, dict):
            return cls()
        try:
            max_points = int(data.get("max_points", CHART_MAX_POINTS_DEFAULT))
        except (TypeError, ValueError):
            max_points = CHART_MAX_POINTS_DEFAULT
        try:
            time_window = float(data.get("time_window_s", 0.0))
        except (TypeError, ValueError):
            time_window = 0.0
        return cls(
            series_id=str(data.get("series_id") or new_id("series")),
            name=str(data.get("name", "Series")),
            enabled=bool(data.get("enabled", True)),
            source_type=str(data.get("source_type", "field")),
            rule_id=str(data.get("rule_id", "")),
            field_name=str(data.get("field_name", "")),
            group_by=str(data.get("group_by", "none")),
            chart_type=str(data.get("chart_type", "line")),
            axis=str(data.get("axis", "left")),
            color=str(data.get("color", "#15d1a3")),
            max_points=max(10, max_points),
            time_window_s=max(0.0, time_window),
            operation=str(data.get("operation", "add")),
            source_a=str(data.get("source_a", "")),
            source_b=str(data.get("source_b", "")),
            op_window=int(data.get("op_window", 100) or 100),
            op_value=float(data.get("op_value", 1.0) or 1.0),
            op_scale=float(data.get("op_scale", 1.0) or 1.0),
        )


class ChartConfig:
    def __init__(self):
        self.enabled = True
        self.capture_when_dialog_closed = False
        self.max_points_default = CHART_MAX_POINTS_DEFAULT
        self.rules: list = []
        self.series: list = []

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "capture_when_dialog_closed": self.capture_when_dialog_closed,
            "max_points_default": self.max_points_default,
            "rules": [r.to_dict() for r in self.rules],
            "series": [s.to_dict() for s in self.series],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChartConfig":
        cfg = cls()
        if not isinstance(data, dict):
            return cfg
        cfg.enabled = bool(data.get("enabled", True))
        cfg.capture_when_dialog_closed = bool(data.get("capture_when_dialog_closed", False))
        try:
            cfg.max_points_default = int(data.get("max_points_default", CHART_MAX_POINTS_DEFAULT))
        except (TypeError, ValueError):
            cfg.max_points_default = CHART_MAX_POINTS_DEFAULT
        cfg.rules = [ChartRule.from_dict(r) for r in (data.get("rules") or [])]
        cfg.series = [ChartSeries.from_dict(s) for s in (data.get("series") or [])]
        return cfg

    def rule_by_id(self, rule_id: str):
        for r in self.rules:
            if r.rule_id == rule_id:
                return r
        return None

    def series_by_id(self, series_id: str):
        for s in self.series:
            if s.series_id == series_id:
                return s
        return None


def now_ts() -> float:
    return time.time()
