import time
from dataclasses import dataclass
from typing import Callable, Optional

from log_config import get_logger

logger = get_logger(__name__)


@dataclass
class StabilizeResult:
    stable: bool
    reason: str
    target: float
    actual: Optional[float]
    waited_s: float
    poll_count: int


class TemperatureStabilizer:
    """Reusable chamber temperature stabilization helper.

    Algorithm:
      1. Arrival phase: poll PV every ``poll_interval`` seconds until
         ``|PV - target| <= arrive_tolerance`` (skipped when arrive_tolerance is None).
      2. Stability phase: keep a sliding window covering ``window_seconds``
         of samples. Require ``max - min < tolerance`` for ``stable_hits``
         consecutive evaluations.
      3. Watchdog: abort with reason="timeout" when total elapsed exceeds
         ``max_wait_s`` (0 means infinite).

    The helper is UI / Qt agnostic: callers pass ``log_fn`` (a plain
    callable that accepts a single string) and ``stop_check`` (returns
    True to request abort). When omitted, messages go to the module
    logger and the loop runs until completion or watchdog.
    """

    def __init__(
        self,
        chamber,
        *,
        poll_interval: float = 5.0,
        window_seconds: float = 60.0,
        tolerance: float = 0.2,
        stable_hits: int = 2,
        max_wait_s: float = 1800.0,
        arrive_tolerance: Optional[float] = 1.0,
        log_fn: Optional[Callable[[str], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None,
        log_progress_every: float = 30.0,
    ) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be > 0")
        if window_seconds < poll_interval:
            raise ValueError("window_seconds must be >= poll_interval")
        if stable_hits < 1:
            raise ValueError("stable_hits must be >= 1")

        self.chamber = chamber
        self.poll_interval = float(poll_interval)
        self.window_seconds = float(window_seconds)
        self.tolerance = float(tolerance)
        self.stable_hits = int(stable_hits)
        self.max_wait_s = float(max_wait_s)
        self.arrive_tolerance = arrive_tolerance
        self._log_fn = log_fn
        self._stop_check = stop_check
        self._log_progress_every = float(log_progress_every)

    def _emit(self, msg: str) -> None:
        if self._log_fn is not None:
            try:
                self._log_fn(msg)
            except Exception:
                logger.debug("log_fn raised, falling back to logger", exc_info=True)
                logger.info(msg)
        else:
            logger.info(msg)

    def _should_stop(self) -> bool:
        if self._stop_check is None:
            return False
        try:
            return bool(self._stop_check())
        except Exception:
            logger.debug("stop_check raised, treating as no-stop", exc_info=True)
            return False

    def _sleep_interruptible(self, seconds: float) -> bool:
        """Sleep up to ``seconds`` while polling stop_check. Returns True if aborted."""
        end = time.time() + seconds
        while True:
            if self._should_stop():
                return True
            remaining = end - time.time()
            if remaining <= 0:
                return False
            time.sleep(min(0.5, remaining))

    def _read_temp(self) -> Optional[float]:
        try:
            return self.chamber.get_current_temp()
        except Exception as e:
            logger.warning("get_current_temp failed: %s", e)
            return None

    def wait_for_stable(self, target: float) -> StabilizeResult:
        window_capacity = max(2, int(round(self.window_seconds / self.poll_interval)))
        history = []
        poll_count = 0
        stable_hits = 0
        arrived = self.arrive_tolerance is None
        t0 = time.time()
        last_progress_log = t0

        while True:
            if self._should_stop():
                return StabilizeResult(
                    stable=False,
                    reason="stopped",
                    target=target,
                    actual=self._read_temp(),
                    waited_s=time.time() - t0,
                    poll_count=poll_count,
                )

            elapsed = time.time() - t0
            if self.max_wait_s > 0 and elapsed > self.max_wait_s:
                actual = self._read_temp()
                self._emit(
                    f"[WARN] Temperature watchdog timeout: target={target:.2f} "
                    f"actual={actual if actual is None else f'{actual:.2f}'} "
                    f"after {elapsed:.0f}s"
                )
                return StabilizeResult(
                    stable=False,
                    reason="timeout",
                    target=target,
                    actual=actual,
                    waited_s=elapsed,
                    poll_count=poll_count,
                )

            actual = self._read_temp()
            poll_count += 1

            if actual is None:
                if self._sleep_interruptible(self.poll_interval):
                    continue
                continue

            if not arrived:
                if abs(actual - target) <= float(self.arrive_tolerance):
                    arrived = True
                    history.clear()
                    self._emit(
                        f"[INFO] Chamber arrived: target={target:.2f} "
                        f"actual={actual:.2f} after {elapsed:.0f}s"
                    )

            history.append(actual)
            if len(history) > window_capacity:
                history.pop(0)

            if arrived and len(history) >= window_capacity:
                spread = max(history) - min(history)
                if spread < self.tolerance:
                    stable_hits += 1
                    if stable_hits >= self.stable_hits:
                        return StabilizeResult(
                            stable=True,
                            reason="stable",
                            target=target,
                            actual=actual,
                            waited_s=time.time() - t0,
                            poll_count=poll_count,
                        )
                else:
                    stable_hits = 0

            now = time.time()
            if now - last_progress_log >= self._log_progress_every:
                phase = "stabilizing" if arrived else "arriving"
                self._emit(
                    f"[INFO] Temp {phase}: target={target:.2f} "
                    f"actual={actual:.2f} elapsed={elapsed:.0f}s "
                    f"hits={stable_hits}/{self.stable_hits}"
                )
                last_progress_log = now

            if self._sleep_interruptible(self.poll_interval):
                continue
