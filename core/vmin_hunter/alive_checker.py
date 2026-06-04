"""VminHunter DUT 判活器（可扩展策略式）。

在每次电压更改并主动触发 STATUS IO 后，需要判断 DUT 是否仍能正常
休眠/唤醒。本模块提供与 UI / 仪器无关的纯逻辑判活器：

- 由上层（core 编排器，运行于 QThread）把 UART LOG 增量喂入，并负责
  推进时间（feed_time），本模块只做无副作用的状态判定。
- 判活策略通过 ``AliveStrategy`` 抽象，便于后续追加新的判活方式
  （如其它 LOG 特征字符串、IO 电平监测等），不影响编排器逻辑。

当前默认策略 ``SleepWakeLogStrategy`` 依据日志：

    key_event_process: sleep=0   -> 唤醒
    key_event_process: sleep=1   -> 休眠

判定规则（按键翻转状态：主动触发两次 STATUS IO 后）：

- PASS : 在判活窗口内同时观察到 sleep=0（唤醒）与 sleep=1（重新休眠），
         不限定先后顺序（按键翻转无法保证首次翻转方向）。
- FAIL : 出现 ASSERT/崩溃关键字；或超时无任何新日志；或超时未凑齐两种翻转。
"""

import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional

from log_config import get_logger

logger = get_logger(__name__)


DEFAULT_CRASH_KEYWORDS = (
    "ASSERT",
    "Assert",
    "assert",
    "Crash",
    "CRASH",
    "Hang",
    "HANG",
    "Fault",
    "FAULT",
    "HardFault",
    "panic",
    "PANIC",
)

DEFAULT_NO_LOG_TIMEOUT_S = 3.0
DEFAULT_SEQUENCE_TIMEOUT_S = 10.0


class AliveState(str, Enum):
    PENDING = "PENDING"
    PASS = "PASS"
    FAIL = "FAIL"


class FailReason(str, Enum):
    NONE = "NONE"
    CRASH_KEYWORD = "CRASH_KEYWORD"
    NO_LOG_TIMEOUT = "NO_LOG_TIMEOUT"
    SEQUENCE_TIMEOUT = "SEQUENCE_TIMEOUT"


@dataclass
class AliveResult:
    state: AliveState = AliveState.PENDING
    fail_reason: FailReason = FailReason.NONE
    detail: str = ""
    matched_lines: List[str] = field(default_factory=list)

    @property
    def is_pass(self) -> bool:
        return self.state is AliveState.PASS

    @property
    def is_fail(self) -> bool:
        return self.state is AliveState.FAIL

    @property
    def is_pending(self) -> bool:
        return self.state is AliveState.PENDING


class AliveStrategy(ABC):
    """判活策略抽象基类。

    上层先调用 ``reset()`` 开启一次判活窗口，然后增量喂入：
    - ``feed_line(line, now)`` : 每收到一行 LOG 调用一次。
    - ``feed_time(now)``       : 周期性调用以推进超时判定（即使无新数据）。

    任一方法返回非 PENDING 的 ``AliveResult`` 即代表本轮判定结束。
    """

    name: str = "base"

    @abstractmethod
    def reset(self, now: Optional[float] = None) -> None:
        ...

    @abstractmethod
    def feed_line(self, line: str, now: Optional[float] = None) -> AliveResult:
        ...

    @abstractmethod
    def feed_time(self, now: Optional[float] = None) -> AliveResult:
        ...


class SleepWakeLogStrategy(AliveStrategy):
    """基于 sleep=0 / sleep=1 翻转的 LOG 判活策略。"""

    name = "sleep_wake_log"

    def __init__(
        self,
        wake_pattern: str = r"key_event_process:\s*sleep=0",
        sleep_pattern: str = r"key_event_process:\s*sleep=1",
        crash_keywords=DEFAULT_CRASH_KEYWORDS,
        no_log_timeout_s: float = DEFAULT_NO_LOG_TIMEOUT_S,
        sequence_timeout_s: float = DEFAULT_SEQUENCE_TIMEOUT_S,
        require_full_cycle: bool = True,
    ):
        self._wake_re = re.compile(wake_pattern)
        self._sleep_re = re.compile(sleep_pattern)
        self._crash_keywords = tuple(crash_keywords)
        self._no_log_timeout_s = float(no_log_timeout_s)
        self._sequence_timeout_s = float(sequence_timeout_s)
        self._require_full_cycle = bool(require_full_cycle)

        self._start_ts = 0.0
        self._last_line_ts = 0.0
        self._any_log = False
        self._woke = False
        self._slept_again = False
        self._matched: List[str] = []

    def reset(self, now: Optional[float] = None) -> None:
        ts = time.monotonic() if now is None else now
        self._start_ts = ts
        self._last_line_ts = ts
        self._any_log = False
        self._woke = False
        self._slept_again = False
        self._matched = []

    def feed_line(self, line: str, now: Optional[float] = None) -> AliveResult:
        ts = time.monotonic() if now is None else now
        self._last_line_ts = ts
        self._any_log = True

        crash = self._match_crash(line)
        if crash is not None:
            self._matched.append(line)
            return AliveResult(
                state=AliveState.FAIL,
                fail_reason=FailReason.CRASH_KEYWORD,
                detail=f"Crash keyword '{crash}' detected",
                matched_lines=list(self._matched),
            )

        if not self._woke and self._wake_re.search(line):
            self._woke = True
            self._matched.append(line)
        elif not self._slept_again and self._sleep_re.search(line):
            self._slept_again = True
            self._matched.append(line)

        if (self._woke and self._slept_again) or (
            (self._woke or self._slept_again) and not self._require_full_cycle
        ):
            return AliveResult(
                state=AliveState.PASS,
                detail="Sleep/wake cycle observed",
                matched_lines=list(self._matched),
            )

        return AliveResult(state=AliveState.PENDING, matched_lines=list(self._matched))

    def feed_time(self, now: Optional[float] = None) -> AliveResult:
        ts = time.monotonic() if now is None else now

        if not self._any_log and (ts - self._start_ts) >= self._no_log_timeout_s:
            return AliveResult(
                state=AliveState.FAIL,
                fail_reason=FailReason.NO_LOG_TIMEOUT,
                detail=f"No log within {self._no_log_timeout_s:.1f}s after trigger",
            )

        if (ts - self._start_ts) >= self._sequence_timeout_s:
            return AliveResult(
                state=AliveState.FAIL,
                fail_reason=FailReason.SEQUENCE_TIMEOUT,
                detail=(
                    f"Expected sleep/wake cycle not seen within "
                    f"{self._sequence_timeout_s:.1f}s "
                    f"(woke={self._woke}, slept_again={self._slept_again})"
                ),
                matched_lines=list(self._matched),
            )

        return AliveResult(state=AliveState.PENDING, matched_lines=list(self._matched))

    def _match_crash(self, line: str) -> Optional[str]:
        for kw in self._crash_keywords:
            if kw in line:
                return kw
        return None


class AliveChecker:
    """判活会话管理器：包裹一个 ``AliveStrategy``，对外提供统一接口。

    典型用法（由 core 编排器在 QThread 中驱动）::

        checker = AliveChecker(SleepWakeLogStrategy())
        checker.start()                     # 主动触发 STATUS IO 之后调用
        # 收到 UART 行:
        result = checker.feed_line(text)
        # 周期 tick（无新数据也要调，用于超时判定）:
        result = checker.tick()
        if result.is_pass or result.is_fail:
            ...
    """

    def __init__(self, strategy: Optional[AliveStrategy] = None):
        self._strategy = strategy or SleepWakeLogStrategy()
        self._result = AliveResult()
        self._finished = False

    @property
    def strategy(self) -> AliveStrategy:
        return self._strategy

    @property
    def result(self) -> AliveResult:
        return self._result

    @property
    def finished(self) -> bool:
        return self._finished

    def start(self, now: Optional[float] = None) -> None:
        self._strategy.reset(now=now)
        self._result = AliveResult()
        self._finished = False
        logger.info("AliveChecker started with strategy '%s'", self._strategy.name)

    def feed_line(self, line: str, now: Optional[float] = None) -> AliveResult:
        if self._finished:
            return self._result
        result = self._strategy.feed_line(line, now=now)
        return self._update(result)

    def tick(self, now: Optional[float] = None) -> AliveResult:
        if self._finished:
            return self._result
        result = self._strategy.feed_time(now=now)
        return self._update(result)

    def _update(self, result: AliveResult) -> AliveResult:
        self._result = result
        if not result.is_pending:
            self._finished = True
            if result.is_fail:
                logger.warning(
                    "AliveChecker FAIL [%s]: %s",
                    result.fail_reason.value, result.detail,
                )
            else:
                logger.info("AliveChecker PASS: %s", result.detail)
        return result
