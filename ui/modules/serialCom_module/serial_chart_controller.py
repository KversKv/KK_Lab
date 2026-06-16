from collections import deque

from PySide6.QtCore import QObject, Signal

from log_config import get_logger
from ui.modules.serialCom_module.serial_chart_model import (
    now_ts,
    parse_channel_filter,
)
from ui.modules.serialCom_module.serial_chart_parser import (
    SerialChartParser,
    ChartSeriesBuffer,
)

logger = get_logger(__name__)

_RECENT_EVENT_MAX = 500


class SerialChartController(QObject):
    series_changed = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config
        self._parser = SerialChartParser(config)
        self._buffers = {}
        self._seq_map = {}
        self._t0 = now_ts()
        self._paused = False
        self._recent_events = deque(maxlen=_RECENT_EVENT_MAX)
        self._events_seen = 0
        self.rebuild_series()

    @property
    def parser(self):
        return self._parser

    @property
    def recent_events(self):
        return list(self._recent_events)

    @property
    def events_seen(self):
        return self._events_seen

    def set_paused(self, paused: bool):
        self._paused = bool(paused)

    def is_paused(self) -> bool:
        return self._paused

    def refresh_config(self):
        self._parser.refresh_rules()
        self.rebuild_series()

    def rebuild_series(self):
        existing = self._buffers
        new_buffers = {}
        for s in self._config.series:
            if s.source_type == "field" and s.group_by != "none":
                continue
            key = s.series_id
            old = existing.get(key)
            if old is not None and old.max_points == s.max_points and old.time_window_s == s.time_window_s:
                new_buffers[key] = old
            else:
                new_buffers[key] = ChartSeriesBuffer(s.max_points, s.time_window_s)
        for key, buf in existing.items():
            if key not in new_buffers and ("::" in key):
                new_buffers[key] = buf
        self._buffers = new_buffers
        self.series_changed.emit()

    def buffer_for(self, series_id, suffix=None):
        key = f"{series_id}::{suffix}" if suffix else series_id
        buf = self._buffers.get(key)
        if buf is None:
            base = self._config.series_by_id(series_id)
            if base is None:
                return None
            buf = ChartSeriesBuffer(base.max_points, base.time_window_s)
            self._buffers[key] = buf
            self.series_changed.emit()
        return buf

    def buffers(self):
        return dict(self._buffers)

    def mark_all_dirty(self):
        for buf in self._buffers.values():
            if buf.xs:
                buf.dirty = True

    def clear(self):
        for buf in self._buffers.values():
            buf.clear()
        self._recent_events.clear()
        self._events_seen = 0
        self._seq_map = {}
        self._t0 = now_ts()

    def feed_line(self, line, session_id="active", rx_time=None):
        if self._paused or not self._config.enabled:
            return
        if rx_time is None:
            rx_time = now_ts()
        events = self._parser.feed_line(line, session_id, rx_time)
        self._dispatch(events)

    def feed_bytes(self, data, session_id="active", rx_time=None):
        if self._paused or not self._config.enabled:
            return
        if rx_time is None:
            rx_time = now_ts()
        events = self._parser.feed_bytes(data, session_id, rx_time)
        self._dispatch(events)

    def _x_value(self, rule, rx_time, seq_key):
        if rule is not None and rule.timestamp_mode == "sequence_index":
            seq = self._seq_map.get(seq_key, 0) + 1
            self._seq_map[seq_key] = seq
            return float(seq)
        return float(rx_time - self._t0)

    def _dispatch(self, events):
        if not events:
            return
        for ev in events:
            self._recent_events.append(ev)
            self._events_seen += 1
            rule = self._config.rule_by_id(ev["rule_id"])
            for s in self._config.series:
                if not s.enabled or s.source_type != "field":
                    continue
                if s.rule_id != ev["rule_id"]:
                    continue
                if s.field_name not in ev["fields"]:
                    continue
                y = ev["fields"][s.field_name]
                if not isinstance(y, (int, float)):
                    continue
                label = ev["labels"].get(s.field_name)
                suffix = self._group_suffix(s, ev)
                if s.group_by == "channel":
                    allow = parse_channel_filter(getattr(s, "channels", ""))
                    if allow is not None and str(suffix) not in allow:
                        continue
                seq_key = f"{s.series_id}::{suffix}" if suffix else s.series_id
                x = self._x_value(rule, ev["rx_time"], seq_key)
                buf = self.buffer_for(s.series_id, suffix)
                if buf is not None:
                    buf.append(x, float(y), label)
        self._update_derived(events)

    def _group_suffix(self, series, ev):
        if series.group_by == "none":
            return None
        if series.group_by == "channel":
            return ev.get("channel")
        if series.group_by == "key":
            return ev.get("key")
        if series.group_by == "session":
            return ev.get("session_id")
        return None

    def _update_derived(self, events):
        for s in self._config.series:
            if not s.enabled or s.source_type != "derived":
                continue
            try:
                self._compute_derived(s)
            except Exception:
                logger.error("Derived series %s failed", s.series_id, exc_info=True)

    def _compute_derived(self, s):
        op = s.operation
        buf_out = self.buffer_for(s.series_id)
        if buf_out is None:
            return

        if op in ("rolling_avg", "rolling_rate"):
            src = self._buffers.get(s.source_a)
            if src is None or not src.xs:
                return
            window = max(1, int(s.op_window))
            ys = list(src.ys)[-window:]
            x = src.xs[-1]
            if op == "rolling_avg":
                val = sum(ys) / len(ys)
            else:
                hits = sum(1 for y in ys if abs(y - s.op_value) < 1e-9)
                val = hits / len(ys)
            self._append_derived(buf_out, x, val * s.op_scale)
            return

        a = self._buffers.get(s.source_a)
        b = self._buffers.get(s.source_b)
        if a is None or b is None or not a.xs or not b.xs:
            return
        xa, ya = a.xs[-1], a.ys[-1]
        yb = b.ys[-1]
        if op == "add":
            val = ya + yb
        elif op == "subtract":
            val = ya - yb
        elif op == "multiply":
            val = ya * yb
        elif op == "divide":
            if abs(yb) < 1e-12:
                return
            val = ya / yb
        else:
            return
        self._append_derived(buf_out, xa, val * s.op_scale)

    def _append_derived(self, buf, x, val):
        if buf.xs and buf.xs[-1] == x:
            return
        buf.append(x, float(val), None)
