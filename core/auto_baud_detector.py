import time
from collections import deque
from enum import Enum

try:
    from PySide6.QtCore import QObject, Signal, QThread
    _HAS_QT = True
except ImportError:
    _HAS_QT = False


AUTO_BAUD_CONFIG = {
    # 候选波特率列表
    "candidate_baudrates": [921600, 1152000, 2000000, 3000000],
    # 监测滑动窗口最小字节数（达到此值且超时后才评估）
    "monitor_window_min_bytes": 32,
    # 监测滑动窗口最大字节数（达到此值立即评估）
    "monitor_window_max_bytes": 1024,
    # 监测滑动窗口最大等待时间（毫秒）
    "monitor_window_max_time_ms": 30,
    # 扫描每个候选波特率的目标采样字节数（达到即停止采样）
    "scan_sample_bytes": 256,
    # 扫描时单个波特率的最大等待超时（毫秒），防止无数据时死等
    "scan_timeout_ms": 100,
    # 切换波特率后等待串口稳定的时间（毫秒）
    "baud_switch_settle_ms": 10,
    # 连续多少个坏窗口后进入 SUSPECT 状态
    "bad_windows_to_suspect": 2,
    # SUSPECT 状态下连续多少个坏窗口后触发扫描
    "suspect_windows_to_scan": 1,
    # 新波特率需要连续胜出的扫描轮数才确认切换
    "confirm_scan_rounds": 2,
    # 成功切换波特率后的冷却时间（毫秒），冷却期间禁止再次自动切换
    "switch_cooldown_ms": 3000,
    # 锁定阈值：评分 >= 此值才认为波特率匹配
    "lock_threshold": 80,
    # 异常阈值：评分 < 此值认为当前波特率可能不匹配
    "bad_threshold": 55,
    # 新波特率必须比当前波特率评分高出的最低分差
    "switch_score_margin": 25,
    # 空闲窗口（无数据）是否视为异常
    "empty_window_is_bad": False,
}

_LOG_KEYWORDS = [
    b"[INFO]", b"[WARN]", b"[ERROR]", b"DEBUG", b"Boot", b"boot",
    b"init", b"OK", b"FAIL",
]

_LOG_CHARS = [ord(b':'), ord(b'='), ord(b'['), ord(b']')]


class AutoBaudState(str, Enum):
    UNKNOWN = "UNKNOWN"
    SCANNING = "SCANNING"
    LOCKED = "LOCKED"
    SUSPECT = "SUSPECT"


def score_rx_data(data: bytes):
    if len(data) == 0:
        return None

    total = len(data)
    score = 0

    printable_count = 0
    whitespace_count = 0
    bad_control_count = 0
    high_bit_count = 0
    zero_ff_count = 0

    for b in data:
        if 0x20 <= b <= 0x7E:
            printable_count += 1
        elif b in (0x0D, 0x0A, 0x09):
            whitespace_count += 1
        elif b < 0x20:
            bad_control_count += 1
        if b >= 0x80:
            high_bit_count += 1
        if b == 0x00 or b == 0xFF:
            zero_ff_count += 1

    text_count = printable_count + whitespace_count
    printable_ratio = printable_count / total
    text_ratio = text_count / total
    bad_control_ratio = bad_control_count / total
    high_bit_ratio = high_bit_count / total
    zero_ff_ratio = zero_ff_count / total

    if printable_ratio >= 0.90:
        score += 45
    elif printable_ratio >= 0.80:
        score += 35
    elif printable_ratio >= 0.65:
        score += 20
    elif printable_ratio >= 0.50:
        score += 5

    if bad_control_ratio <= 0.01:
        score += 15
    elif bad_control_ratio <= 0.03:
        score += 8
    elif bad_control_ratio > 0.08:
        score -= 20

    has_newline = b'\n' in data or b'\r\n' in data
    if has_newline:
        lines = data.split(b'\n')
        non_empty_lines = [ln.rstrip(b'\r') for ln in lines if ln.rstrip(b'\r')]
        reasonable_lines = sum(
            1 for ln in non_empty_lines
            if 12 <= len(ln) <= 200
            and sum(1 for c in ln if 0x20 <= c <= 0x7E) / len(ln) >= 0.80
        )
        if non_empty_lines and reasonable_lines >= len(non_empty_lines) * 0.5:
            score += 15
            if len(non_empty_lines) >= 3:
                score += 10
        elif non_empty_lines and reasonable_lines >= len(non_empty_lines) * 0.3:
            score += 5
    lone_cr_count = data.count(b'\r') - data.count(b'\r\n')
    if lone_cr_count > total * 0.05:
        score -= 5

    keyword_hits = sum(1 for kw in _LOG_KEYWORDS if kw in data)
    char_hits = sum(1 for c in _LOG_CHARS if c in data)
    pattern_hits = keyword_hits + (1 if char_hits >= 2 else 0)
    if pattern_hits >= 2:
        score += 15
    elif pattern_hits >= 1:
        score += 10

    try:
        data.decode('ascii')
        score += 10
    except UnicodeDecodeError:
        try:
            data.decode('utf-8')
            score += 5
        except UnicodeDecodeError:
            pass

    if high_bit_ratio > 0.30:
        score -= 30
    elif high_bit_ratio > 0.15:
        score -= 20
    elif high_bit_ratio > 0.05:
        score -= 10
    if zero_ff_ratio > 0.20:
        score -= 15

    return max(0, min(100, score))


if _HAS_QT:
    class AutoBaudScanWorker(QObject):
        scan_finished = Signal(dict)
        scan_progress = Signal(str)
        state_changed = Signal(str)
        score_update = Signal(int)
        baudrate_changed = Signal(int)

        def __init__(self, serial_conn, config=None, current_baudrate=None):
            super().__init__()
            self._serial_conn = serial_conn
            self._config = config or dict(AUTO_BAUD_CONFIG)
            self._current_baudrate = current_baudrate
            self._running = True

        def stop(self):
            self._running = False

        def run_initial_scan(self):
            self.state_changed.emit(AutoBaudState.SCANNING.value)
            self.scan_progress.emit("[INFO] Start scanning candidate baudrates...")

            candidates = self._config["candidate_baudrates"]
            results = []

            for baud in candidates:
                if not self._running:
                    self.scan_finished.emit({"success": False, "reason": "stopped"})
                    return
                try:
                    self._serial_conn.baudrate = baud
                except Exception as e:
                    self.scan_progress.emit(f"[WARN] Cannot set baudrate {baud}: {e}")
                    results.append({"baudrate": baud, "score": -1, "sample_len": 0})
                    continue

                QThread.msleep(self._config["baud_switch_settle_ms"])

                if self._serial_conn.in_waiting > 0:
                    self._serial_conn.read(self._serial_conn.in_waiting)

                data = self._read_sample()
                s = score_rx_data(data)
                if s is None:
                    s = 0
                results.append({"baudrate": baud, "score": s, "sample_len": len(data)})
                self.scan_progress.emit(
                    f"[INFO] {baud} score={s} sample={len(data)} bytes"
                )

            valid = [r for r in results if r["score"] >= 0]
            if not valid:
                self.scan_finished.emit({"success": False, "reason": "no_valid_baudrate", "results": results})
                return

            best = max(valid, key=lambda x: x["score"])
            lock_threshold = self._config["lock_threshold"]

            if best["score"] >= lock_threshold:
                try:
                    self._serial_conn.baudrate = best["baudrate"]
                except Exception as e:
                    self.scan_finished.emit({"success": False, "reason": f"set_baud_failed: {e}", "results": results})
                    return
                self.scan_progress.emit(
                    f"[INFO] Locked baudrate: {best['baudrate']}, score={best['score']}"
                )
                self.baudrate_changed.emit(best["baudrate"])
                self.state_changed.emit(AutoBaudState.LOCKED.value)
                self.scan_finished.emit({
                    "success": True,
                    "baudrate": best["baudrate"],
                    "score": best["score"],
                    "results": results,
                })
            else:
                if self._current_baudrate:
                    try:
                        self._serial_conn.baudrate = self._current_baudrate
                    except Exception:
                        pass
                self.scan_finished.emit({
                    "success": False,
                    "reason": "no_baudrate_above_threshold",
                    "results": results,
                    "best": best,
                })

        def run_runtime_rescan(self):
            self.state_changed.emit(AutoBaudState.SCANNING.value)
            self.scan_progress.emit("[INFO] Runtime rescan started...")

            candidates = self._config["candidate_baudrates"]
            confirm_rounds = self._config["confirm_scan_rounds"]
            lock_threshold = self._config["lock_threshold"]
            switch_margin = self._config["switch_score_margin"]
            original_baud = self._current_baudrate

            if not self._running:
                self._restore_baudrate(original_baud)
                self.scan_finished.emit({"success": False, "reason": "stopped"})
                return

            results = []
            for baud in candidates:
                if not self._running:
                    self._restore_baudrate(original_baud)
                    self.scan_finished.emit({"success": False, "reason": "stopped"})
                    return
                try:
                    self._serial_conn.baudrate = baud
                except Exception as e:
                    self.scan_progress.emit(f"[WARN] Cannot set baudrate {baud}: {e}")
                    results.append({"baudrate": baud, "score": -1, "sample_len": 0})
                    continue

                QThread.msleep(self._config["baud_switch_settle_ms"])
                if self._serial_conn.in_waiting > 0:
                    self._serial_conn.read(self._serial_conn.in_waiting)

                data = self._read_sample()
                s = score_rx_data(data)
                if s is None:
                    s = 0
                results.append({"baudrate": baud, "score": s, "sample_len": len(data)})

            for r in results:
                self.scan_progress.emit(
                    f"[INFO] Round 1: {r['baudrate']} score={r['score']} sample={r['sample_len']} bytes"
                )

            valid = [r for r in results if r["score"] >= 0]
            if not valid:
                self._restore_baudrate(original_baud)
                self.scan_progress.emit("[INFO] Recheck failed. Keep current baudrate.")
                self.state_changed.emit(AutoBaudState.LOCKED.value)
                self.scan_finished.emit({"success": False, "reason": "no_winner"})
                return

            best = max(valid, key=lambda x: x["score"])
            if best["score"] < lock_threshold or best["baudrate"] == original_baud:
                self._restore_baudrate(original_baud)
                self.scan_progress.emit("[INFO] Recheck failed. Keep current baudrate.")
                self.state_changed.emit(AutoBaudState.LOCKED.value)
                self.scan_finished.emit({"success": False, "reason": "not_confirmed"})
                return

            for confirm_idx in range(1, confirm_rounds):
                if not self._running:
                    self._restore_baudrate(original_baud)
                    self.scan_finished.emit({"success": False, "reason": "stopped"})
                    return

                try:
                    self._serial_conn.baudrate = best["baudrate"]
                except Exception as e:
                    self._restore_baudrate(original_baud)
                    self.scan_finished.emit({"success": False, "reason": f"set_baud_failed: {e}"})
                    return

                QThread.msleep(self._config["baud_switch_settle_ms"])
                if self._serial_conn.in_waiting > 0:
                    self._serial_conn.read(self._serial_conn.in_waiting)

                data = self._read_sample()
                s = score_rx_data(data)
                if s is None:
                    s = 0

                self.scan_progress.emit(
                    f"[INFO] Round {confirm_idx+1}: {best['baudrate']} score={s} sample={len(data)} bytes"
                )

                if s < lock_threshold:
                    self._restore_baudrate(original_baud)
                    self.scan_progress.emit("[INFO] Recheck failed. Keep current baudrate.")
                    self.state_changed.emit(AutoBaudState.LOCKED.value)
                    self.scan_finished.emit({"success": False, "reason": "confirm_failed"})
                    return

            candidate_baud = best["baudrate"]
            avg_score = best["score"]
            if avg_score >= (getattr(self, '_recent_score_avg', 0) + switch_margin):
                try:
                    self._serial_conn.baudrate = candidate_baud
                except Exception as e:
                    self._restore_baudrate(original_baud)
                    self.scan_finished.emit({"success": False, "reason": f"set_baud_failed: {e}"})
                    return
                self.scan_progress.emit(
                    f"[INFO] Confirmed baudrate change: {original_baud} -> {candidate_baud}"
                )
                self.baudrate_changed.emit(candidate_baud)
                self.state_changed.emit(AutoBaudState.LOCKED.value)
                self.scan_finished.emit({
                    "success": True,
                    "baudrate": candidate_baud,
                    "score": int(avg_score),
                    "results": [],
                })
                return

            self._restore_baudrate(original_baud)
            self.scan_progress.emit(
                f"[INFO] Recheck failed. Keep current baudrate: {original_baud}"
            )
            self.state_changed.emit(AutoBaudState.LOCKED.value)
            self.scan_finished.emit({"success": False, "reason": "not_confirmed"})

        def set_recent_score_avg(self, avg):
            self._recent_score_avg = avg

        def _restore_baudrate(self, baud):
            if baud is not None:
                try:
                    self._serial_conn.baudrate = baud
                except Exception:
                    pass

        def _read_sample(self):
            target_bytes = self._config["scan_sample_bytes"]
            timeout = self._config["scan_timeout_ms"] / 1000.0

            buf = bytearray()
            start = time.perf_counter()

            while self._running:
                if len(buf) >= target_bytes:
                    break
                elapsed = time.perf_counter() - start
                if elapsed >= timeout:
                    break
                try:
                    waiting = self._serial_conn.in_waiting
                    if waiting > 0:
                        chunk = self._serial_conn.read(min(waiting, target_bytes - len(buf)))
                        buf.extend(chunk)
                    else:
                        QThread.msleep(5)
                except Exception:
                    break

            return bytes(buf)


class AutoBaudMonitor:
    def __init__(self, config=None):
        self._config = config or dict(AUTO_BAUD_CONFIG)
        self._state = AutoBaudState.UNKNOWN
        self._monitor_buf = bytearray()
        self._monitor_start_time = time.perf_counter()
        self._bad_window_count = 0
        self._suspect_window_count = 0
        self._last_switch_time = 0.0
        self._recent_scores = deque(maxlen=10)
        self._enabled = False
        self._runtime_redetect_enabled = False
        self._hex_mode = False

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    @property
    def runtime_redetect_enabled(self):
        return self._runtime_redetect_enabled

    @runtime_redetect_enabled.setter
    def runtime_redetect_enabled(self, value):
        self._runtime_redetect_enabled = value

    @property
    def hex_mode(self):
        return self._hex_mode

    @hex_mode.setter
    def hex_mode(self, value):
        self._hex_mode = value

    @property
    def bad_window_count(self):
        return self._bad_window_count

    @property
    def suspect_window_count(self):
        return self._suspect_window_count

    @property
    def recent_score_avg(self):
        if not self._recent_scores:
            return 0
        return sum(self._recent_scores) / len(self._recent_scores)

    @property
    def in_cooldown(self):
        cooldown_ms = self._config["switch_cooldown_ms"]
        elapsed_ms = (time.perf_counter() - self._last_switch_time) * 1000
        return elapsed_ms < cooldown_ms

    def update_config(self, config):
        self._config = config

    def reset(self):
        self._monitor_buf = bytearray()
        self._monitor_start_time = time.perf_counter()
        self._bad_window_count = 0
        self._suspect_window_count = 0
        self._recent_scores.clear()

    def mark_switch(self):
        self._last_switch_time = time.perf_counter()

    def on_rx_data(self, data: bytes):
        if not self._enabled or not self._runtime_redetect_enabled:
            return None
        if self._state not in (AutoBaudState.LOCKED, AutoBaudState.SUSPECT):
            return None
        if self.in_cooldown:
            return None

        self._monitor_buf.extend(data)

        if not self._window_ready():
            return None

        window_data = bytes(self._monitor_buf)
        self._monitor_buf = bytearray()
        self._monitor_start_time = time.perf_counter()

        s = score_rx_data(window_data)
        if s is None:
            return None

        self._recent_scores.append(s)

        bad_threshold = self._config["bad_threshold"]
        bad_windows_to_suspect = self._config["bad_windows_to_suspect"]
        suspect_windows_to_scan = self._config["suspect_windows_to_scan"]

        if self._hex_mode:
            bad_windows_to_suspect = max(bad_windows_to_suspect, 5)
            suspect_windows_to_scan = max(suspect_windows_to_scan, 3)

        if s >= bad_threshold:
            self._bad_window_count = 0
            self._suspect_window_count = 0
            if self._state == AutoBaudState.SUSPECT:
                self._state = AutoBaudState.LOCKED
                return {"action": "recovered", "score": s}
            return {"action": "ok", "score": s}

        self._bad_window_count += 1

        if self._state == AutoBaudState.LOCKED:
            if self._bad_window_count >= bad_windows_to_suspect:
                self._state = AutoBaudState.SUSPECT
                self._suspect_window_count = 0
                return {"action": "suspect", "score": s}
            return {"action": "bad_window", "score": s, "count": self._bad_window_count}

        if self._state == AutoBaudState.SUSPECT:
            self._suspect_window_count += 1
            if self._suspect_window_count >= suspect_windows_to_scan:
                self._state = AutoBaudState.SCANNING
                return {"action": "scan_needed", "score": s}
            return {"action": "suspect_window", "score": s, "count": self._suspect_window_count}

        return None

    def _window_ready(self):
        min_bytes = self._config["monitor_window_min_bytes"]
        max_bytes = self._config["monitor_window_max_bytes"]
        max_time_ms = self._config["monitor_window_max_time_ms"]

        if len(self._monitor_buf) >= max_bytes:
            return True
        elapsed_ms = (time.perf_counter() - self._monitor_start_time) * 1000
        if elapsed_ms >= max_time_ms and len(self._monitor_buf) >= min_bytes:
            return True
        return False
