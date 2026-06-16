import re
import time
from collections import deque

from log_config import get_logger
from ui.modules.serialCom_module.serial_chart_model import (
    ChartRule,
    PASS_FAIL_DEFAULT_MAP,
    CHART_LINE_MAX_LEN,
    CHART_FRAME_MAX_LINES,
    CHART_FRAME_MAX_BYTES,
    CHART_FRAME_TIMEOUT_MS,
)

logger = get_logger(__name__)

_NUM_RE = re.compile(r"[+-]?(?:0[xX][0-9a-fA-F]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
_BOOL_TRUE = {"true", "1", "on", "yes", "high"}
_BOOL_FALSE = {"false", "0", "off", "no", "low"}


def coerce_value(raw, field_type, field_spec=None):
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None

    if field_type in ("int", "float"):
        m = _NUM_RE.search(text)
        if not m:
            return None
        token = m.group(0)
        try:
            if token.lower().startswith(("0x", "+0x", "-0x")):
                val = int(token, 16)
            elif field_type == "int":
                val = int(float(token))
            else:
                val = float(token)
        except (TypeError, ValueError):
            return None
        return float(val) if field_type == "float" else int(val)

    if field_type == "bool":
        low = text.lower()
        if low in _BOOL_TRUE:
            return 1
        if low in _BOOL_FALSE:
            return 0
        m = _NUM_RE.search(text)
        if m:
            try:
                return 1 if float(m.group(0)) != 0 else 0
            except (TypeError, ValueError):
                return None
        return None

    if field_type == "pass_fail":
        mapping = {}
        if field_spec is not None and field_spec.pass_fail_map:
            mapping = {str(k).upper(): v for k, v in field_spec.pass_fail_map.items()}
        if not mapping:
            mapping = PASS_FAIL_DEFAULT_MAP
        key = text.upper()
        if key in mapping:
            try:
                return int(mapping[key])
            except (TypeError, ValueError):
                return None
        return None

    if field_type == "enum":
        if field_spec is not None and field_spec.enum_map:
            values = field_spec.enum_map.get("values") or {}
            if text in values:
                try:
                    return float(values[text])
                except (TypeError, ValueError):
                    return None
            up = text.upper()
            for k, v in values.items():
                if str(k).upper() == up:
                    try:
                        return float(v)
                    except (TypeError, ValueError):
                        return None
        return None

    return text


def enum_label(field_spec, value):
    if field_spec is None or not field_spec.enum_map:
        return None
    labels = field_spec.enum_map.get("labels") or {}
    key = str(int(value)) if float(value).is_integer() else str(value)
    return labels.get(key)


class _FrameState:
    def __init__(self):
        self.active = False
        self.lines = []
        self.bytes_count = 0
        self.start_ts = 0.0


class SerialChartParser:
    def __init__(self, config):
        self._config = config
        self._compiled = {}
        self._compile_errors = {}
        self._frame_states = {}
        self._error_counts = {}
        self.refresh_rules()

    def refresh_rules(self):
        self._compiled = {}
        self._compile_errors = {}
        for rule in self._config.rules:
            if rule.match_mode in ("regex", "frame", "prefix_suffix", "custom_enum") and rule.regex:
                self._compile_rule(rule)

    def _compile_rule(self, rule: ChartRule):
        flags = 0 if rule.case_sensitive else re.IGNORECASE
        try:
            self._compiled[rule.rule_id] = re.compile(rule.regex, flags)
            self._compile_errors.pop(rule.rule_id, None)
        except re.error as exc:
            self._compile_errors[rule.rule_id] = str(exc)
            self._compiled.pop(rule.rule_id, None)
            logger.warning("Chart rule regex compile failed: %s", exc)

    def validate_regex(self, pattern, case_sensitive=False):
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            re.compile(pattern, flags)
            return True, ""
        except re.error as exc:
            return False, str(exc)

    def compile_error(self, rule_id):
        return self._compile_errors.get(rule_id)

    def feed_line(self, line, session_id, rx_time):
        if len(line) > CHART_LINE_MAX_LEN:
            line = line[:CHART_LINE_MAX_LEN]
        events = []
        for rule in self._config.rules:
            if not rule.enabled or rule.input_mode != "line":
                continue
            if not self._session_match(rule, session_id):
                continue
            try:
                events.extend(self._apply_rule(rule, line, session_id, rx_time))
            except Exception:
                self._error_counts[rule.rule_id] = self._error_counts.get(rule.rule_id, 0) + 1
                logger.error("Chart rule %s failed", rule.rule_id, exc_info=True)
        return events

    def feed_bytes(self, data, session_id, rx_time):
        events = []
        hex_str = data.hex(" ")
        for rule in self._config.rules:
            if not rule.enabled or rule.input_mode not in ("bytes_hex", "bytes_raw"):
                continue
            if not self._session_match(rule, session_id):
                continue
            text = hex_str if rule.input_mode == "bytes_hex" else data.decode("latin-1", errors="replace")
            try:
                events.extend(self._apply_rule(rule, text, session_id, rx_time))
            except Exception:
                self._error_counts[rule.rule_id] = self._error_counts.get(rule.rule_id, 0) + 1
                logger.error("Chart rule %s failed", rule.rule_id, exc_info=True)
        return events

    def _session_match(self, rule, session_id):
        if rule.source_session in ("all", ""):
            return True
        if rule.source_session == "active":
            return session_id in ("active", "primary", None)
        return rule.source_session == session_id

    def _apply_rule(self, rule, text, session_id, rx_time):
        if rule.match_mode == "frame":
            return self._apply_frame(rule, text, session_id, rx_time)
        return self._match_text(rule, text, session_id, rx_time)

    def _apply_frame(self, rule, line, session_id, rx_time):
        state = self._frame_states.setdefault(rule.rule_id, _FrameState())
        now = time.monotonic() * 1000
        start = rule.frame_start or rule.keyword_before
        end = rule.frame_end or rule.keyword_after

        if state.active and (
            len(state.lines) >= CHART_FRAME_MAX_LINES
            or state.bytes_count >= CHART_FRAME_MAX_BYTES
            or (now - state.start_ts) > CHART_FRAME_TIMEOUT_MS
        ):
            logger.warning("Chart frame rule %s discarded (overflow/timeout)", rule.rule_id)
            state.active = False
            state.lines = []
            state.bytes_count = 0

        if not state.active:
            if start and start in line:
                state.active = True
                state.lines = [line]
                state.bytes_count = len(line)
                state.start_ts = now
            return []

        state.lines.append(line)
        state.bytes_count += len(line)
        if end and end in line:
            frame_text = "\n".join(state.lines)
            state.active = False
            state.lines = []
            state.bytes_count = 0
            return self._match_text(rule, frame_text, session_id, rx_time)
        return []

    def _match_text(self, rule, text, session_id, rx_time):
        events = []
        compiled = self._compiled.get(rule.rule_id)

        if rule.match_mode == "contains":
            kw = rule.keyword_before
            if kw and (kw in text if rule.case_sensitive else kw.lower() in text.lower()):
                pass
            elif kw:
                return []

        if rule.match_mode == "prefix_suffix":
            extracted = self._extract_prefix_suffix(rule, text)
            if extracted is None:
                return []
            ev = self._build_event(rule, {"value": extracted}, text, session_id, rx_time)
            if ev:
                events.append(ev)
            return events

        if compiled is None:
            if rule.match_mode in ("regex", "custom_enum"):
                return []
            if rule.match_mode == "contains":
                ev = self._build_event(rule, {}, text, session_id, rx_time)
                if ev:
                    events.append(ev)
            return events

        matches = list(compiled.finditer(text))
        if not matches:
            return []
        if rule.emit_policy == "first_match":
            matches = matches[:1]
        elif rule.emit_policy == "last_match_per_line":
            matches = matches[-1:]

        for m in matches:
            groups = m.groupdict() or {}
            if not groups and m.groups():
                groups = {"value": m.group(1)}
            ev = self._build_event(rule, groups, text, session_id, rx_time)
            if ev:
                events.append(ev)
        return events

    def _extract_prefix_suffix(self, rule, text):
        before = rule.keyword_before
        after = rule.keyword_after
        seg = text
        if before:
            idx = text.find(before) if rule.case_sensitive else text.lower().find(before.lower())
            if idx < 0:
                return None
            seg = text[idx + len(before):]
        if after:
            idx = seg.find(after) if rule.case_sensitive else seg.lower().find(after.lower())
            if idx < 0:
                return None
            seg = seg[:idx]
        return seg.strip()

    def _build_event(self, rule, raw_groups, source_text, session_id, rx_time):
        fields = {}
        labels = {}
        channel = raw_groups.get("channel")
        key = raw_groups.get("key")

        specs = {fs.name: fs for fs in rule.field_specs}

        if rule.field_specs:
            for fs in rule.field_specs:
                raw = raw_groups.get(fs.name)
                if raw is None:
                    continue
                val = coerce_value(raw, fs.type, fs)
                if val is None:
                    continue
                fields[fs.name] = val
                if fs.type == "enum":
                    lbl = enum_label(fs, val)
                    if lbl:
                        labels[fs.name] = lbl
        else:
            for gname, gval in raw_groups.items():
                if gname in ("channel", "key"):
                    continue
                if gval is None:
                    continue
                val = coerce_value(gval, "float")
                if val is None:
                    val = gval
                fields[gname] = val

        if not fields:
            return None

        return {
            "rule_id": rule.rule_id,
            "session_id": session_id or "active",
            "rx_time": rx_time,
            "line": source_text,
            "fields": fields,
            "labels": labels,
            "channel": channel,
            "key": key,
        }


class ChartSeriesBuffer:
    def __init__(self, max_points, time_window_s=0.0):
        self.max_points = max(10, int(max_points))
        self.time_window_s = float(time_window_s or 0.0)
        self.xs = deque(maxlen=self.max_points)
        self.ys = deque(maxlen=self.max_points)
        self.labels = deque(maxlen=self.max_points)
        self.dirty = False

    def append(self, x, y, label=None):
        self.xs.append(x)
        self.ys.append(y)
        self.labels.append(label)
        self.dirty = True
        self._trim_time()

    def _trim_time(self):
        if self.time_window_s <= 0 or not self.xs:
            return
        cutoff = self.xs[-1] - self.time_window_s
        while self.xs and self.xs[0] < cutoff:
            self.xs.popleft()
            self.ys.popleft()
            self.labels.popleft()

    def latest(self):
        if not self.xs:
            return None
        return self.xs[-1], self.ys[-1]

    def data(self):
        return list(self.xs), list(self.ys)

    def clear(self):
        self.xs.clear()
        self.ys.clear()
        self.labels.clear()
        self.dirty = True
