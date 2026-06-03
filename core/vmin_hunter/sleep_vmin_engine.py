"""外供电睡眠电压（Sleep Vmin）探底引擎。

对应手动测试流程（External Supply 模式）：

1. 给芯片 Vcore 外供电，唤醒电压取最高值 ``wake_voltage``。
2. 通过 IIC 接口把芯片内部电源输出调到最低值（``init_internal_supply`` 回调），
   避免内部电源影响外部供电准确性；整个遍历开始前只执行一次。
3. 从高到低遍历睡眠 Vcore 电压 ``sleep_points``，每个睡眠电压点：
   a. 先在 ``wake_voltage`` 保持；
   b. 通过 STATUS IO 让芯片进入睡眠；
   c. 等待 ``pre_drop_delay_s``（默认 100ms）后，把 Vcore 降到当前睡眠电压；
   d. 保持 ``sleep_hold_s``（默认 3s）；
   e. 将 Vcore 恢复到 ``wake_voltage``；
   f. 通过 STATUS IO 让芯片唤醒。
4. 每个睡眠电压点完成后，在 ``wake_voltage`` 条件下用 STATUS IO 触发一次完整
   睡眠/唤醒，配合 ``AliveChecker`` 判断 DUT 是否正常。
5. 最低的判活 PASS 的睡眠电压即 Sleep Vmin。

本引擎与 UI / 具体仪器驱动解耦：所有硬件动作（设电压 / STATUS 睡眠 / STATUS
唤醒）由上层通过 ``EngineHooks`` 注入的同步回调执行；DUT 的 UART 日志由上层通过
``feed_uart_line`` 线程安全地喂入。引擎自身运行在 QThread（``run`` 为阻塞循环），
通过信号把日志与结果回填到 UI。
"""

import queue
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from PySide6.QtCore import QObject, QThread, Signal

from log_config import get_logger
from core.vmin_hunter.alive_checker import (
    AliveChecker,
    AliveStrategy,
    SleepWakeLogStrategy,
    AliveState,
)

logger = get_logger(__name__)


@dataclass
class SleepVminConfig:
    wake_voltage: float
    sleep_points: List[float]
    channel: int = 1
    current_limit: float = 1.0
    pre_drop_delay_s: float = 0.1
    sleep_hold_s: float = 3.0
    wake_settle_s: float = 0.1
    status_settle_s: float = 0.1
    alive_poll_interval_s: float = 0.05
    test_cnt: int = 1
    temperature: Optional[float] = None


@dataclass
class EngineHooks:
    """上层注入的同步硬件动作回调（在引擎线程内被调用）。

    所有回调都应是同步阻塞的；异常将由引擎捕获并判 FAIL。
    """

    set_voltage: Callable[[int, float], None]
    output_on: Callable[[int], None]
    status_sleep: Callable[[], None]
    status_wake: Callable[[], None]
    output_off: Optional[Callable[[int], None]] = None
    init_internal_supply: Optional[Callable[[], None]] = None


@dataclass
class SleepVminResult:
    vmin: Optional[float] = None
    last_pass_voltage: Optional[float] = None
    first_fail_voltage: Optional[float] = None
    rows: List[dict] = field(default_factory=list)
    stopped: bool = False


class SleepVminEngine(QObject):
    """外供电睡眠 Vmin 探底引擎（运行于工作线程）。"""

    log_message = Signal(str)
    result_row = Signal(float, object, str, int, str, str)
    vmin_found = Signal(object)
    progress = Signal(int, int)
    finished = Signal(bool, str)

    def __init__(
        self,
        config: SleepVminConfig,
        hooks: EngineHooks,
        strategy: Optional[AliveStrategy] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._cfg = config
        self._hooks = hooks
        self._strategy = strategy or SleepWakeLogStrategy()
        self._uart_queue: "queue.Queue[str]" = queue.Queue()
        self._stop_flag = False
        self._result = SleepVminResult()

    # ------------------------------------------------------------------
    # 外部接口
    # ------------------------------------------------------------------
    def stop(self) -> None:
        self._stop_flag = True

    def feed_uart_line(self, line: str) -> None:
        if line:
            self._uart_queue.put(line)

    @property
    def result(self) -> SleepVminResult:
        return self._result

    # ------------------------------------------------------------------
    # 主循环（在工作线程中执行）
    # ------------------------------------------------------------------
    def run(self) -> None:
        try:
            self._run_sweep()
        except Exception as exc:
            logger.error("SleepVminEngine crashed: %s", exc, exc_info=True)
            self.log_message.emit(f"[ERROR] Engine crashed: {exc}")
            self.finished.emit(False, str(exc))

    def _run_sweep(self) -> None:
        cfg = self._cfg
        temp = cfg.temperature
        ch = cfg.channel

        self.log_message.emit(
            f"[START] Sleep Vmin sweep: wake={cfg.wake_voltage:.3f}V, "
            f"points={cfg.sleep_points}"
        )

        self._safe_hook("set_voltage", lambda: self._hooks.set_voltage(ch, cfg.wake_voltage))
        self._safe_hook("output_on", lambda: self._hooks.output_on(ch))
        time.sleep(cfg.wake_settle_s)

        if self._hooks.init_internal_supply is not None:
            self.log_message.emit(
                "[INIT] IIC: set chip internal supply to minimum"
            )
            self._safe_hook("init_internal_supply", self._hooks.init_internal_supply)
            time.sleep(cfg.wake_settle_s)

        total = len(cfg.sleep_points)
        last_pass: Optional[float] = None

        for idx, sleep_v in enumerate(cfg.sleep_points):
            if self._stop_flag:
                self.log_message.emit("[STOP] Stopped by user.")
                self._result.stopped = True
                self._finalize(last_pass)
                return

            self.progress.emit(idx + 1, total)
            self.log_message.emit(
                f"[STEP {idx + 1}/{total}] Sleep voltage = {sleep_v:.3f} V"
            )

            ok = self._run_one_sleep_point(sleep_v)
            if not ok:
                continue

            status, note = self._run_alive_check(sleep_v)
            self._emit_row(sleep_v, temp, ch, status, note)

            if status == "PASS":
                last_pass = sleep_v
                self._result.last_pass_voltage = sleep_v
            else:
                self._result.first_fail_voltage = sleep_v
                self.log_message.emit(
                    f"[FAIL] DUT abnormal at sleep={sleep_v:.3f} V ({note}); "
                    f"stop hunting."
                )
                break

        self._finalize(last_pass)

    # ------------------------------------------------------------------
    # 单个睡眠电压点的睡眠/降压/恢复/唤醒流程
    # ------------------------------------------------------------------
    def _run_one_sleep_point(self, sleep_v: float) -> bool:
        cfg = self._cfg
        ch = cfg.channel
        try:
            self._hooks.set_voltage(ch, cfg.wake_voltage)
            time.sleep(cfg.wake_settle_s)

            self.log_message.emit("[SEQ] STATUS -> sleep")
            self._hooks.status_sleep()
            time.sleep(cfg.pre_drop_delay_s)

            self.log_message.emit(f"[SEQ] Drop Vcore -> {sleep_v:.3f} V (hold {cfg.sleep_hold_s:.1f}s)")
            self._hooks.set_voltage(ch, sleep_v)
            if self._sleep_with_stop(cfg.sleep_hold_s):
                return False

            self.log_message.emit(f"[SEQ] Restore Vcore -> {cfg.wake_voltage:.3f} V")
            self._hooks.set_voltage(ch, cfg.wake_voltage)
            time.sleep(cfg.wake_settle_s)

            self.log_message.emit("[SEQ] STATUS -> wake")
            self._hooks.status_wake()
            time.sleep(cfg.status_settle_s)
            return True
        except Exception as exc:
            logger.error("Sleep point %.3fV sequence failed: %s", sleep_v, exc, exc_info=True)
            self.log_message.emit(f"[ERROR] Sequence failed at {sleep_v:.3f} V: {exc}")
            return False

    # ------------------------------------------------------------------
    # 判活：wake_voltage 下触发一次完整睡眠/唤醒，喂 UART LOG 判定
    # ------------------------------------------------------------------
    def _run_alive_check(self, sleep_v: float):
        cfg = self._cfg
        checker = AliveChecker(self._strategy)

        self._drain_uart_queue()

        try:
            self.log_message.emit("[ALIVE] STATUS -> sleep (alive probe)")
            self._hooks.status_sleep()
            time.sleep(cfg.status_settle_s)
            self.log_message.emit("[ALIVE] STATUS -> wake (alive probe)")
            self._hooks.status_wake()
        except Exception as exc:
            logger.error("Alive probe trigger failed: %s", exc, exc_info=True)
            return "FAIL", f"status trigger error: {exc}"

        checker.start()
        while True:
            if self._stop_flag:
                return "FAIL", "stopped during alive check"

            try:
                line = self._uart_queue.get(timeout=cfg.alive_poll_interval_s)
            except queue.Empty:
                result = checker.tick()
            else:
                self.log_message.emit(f"[DUT] {line}")
                result = checker.feed_line(line)

            if result.state is AliveState.PASS:
                return "PASS", result.detail
            if result.state is AliveState.FAIL:
                return "FAIL", f"{result.fail_reason.value}: {result.detail}"

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------
    def _drain_uart_queue(self) -> None:
        try:
            while True:
                self._uart_queue.get_nowait()
        except queue.Empty:
            pass

    def _sleep_with_stop(self, seconds: float) -> bool:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._stop_flag:
                return True
            time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
        return False

    def _safe_hook(self, name: str, fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception as exc:
            logger.error("Hook '%s' failed: %s", name, exc, exc_info=True)
            self.log_message.emit(f"[ERROR] Hook '{name}' failed: {exc}")
            raise

    def _emit_row(self, sleep_v, temp, ch, status, note) -> None:
        self._result.rows.append({
            "voltage": sleep_v,
            "temperature": temp,
            "channel": ch,
            "status": status,
            "note": note,
        })
        self.result_row.emit(sleep_v, temp, f"CH{ch}", 1, status, note)

    def _finalize(self, last_pass: Optional[float]) -> None:
        self._result.vmin = last_pass
        self.vmin_found.emit(last_pass)
        if last_pass is not None:
            self.log_message.emit(f"[DONE] Sleep Vmin = {last_pass:.3f} V")
        else:
            self.log_message.emit("[DONE] No passing sleep voltage found.")
        self.finished.emit(True, "")


class SleepVminRunner(QObject):
    """把 ``SleepVminEngine`` 搬到 QThread 运行的封装（供 UI 持有）。"""

    def __init__(self, engine: SleepVminEngine, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._engine = engine
        self._thread = QThread()
        self._engine.moveToThread(self._thread)
        self._thread.started.connect(self._engine.run)
        self._engine.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._thread.deleteLater)

    @property
    def engine(self) -> SleepVminEngine:
        return self._engine

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._engine.stop()

    def is_running(self) -> bool:
        return self._thread.isRunning()

    def feed_uart_line(self, line: str) -> None:
        self._engine.feed_uart_line(line)
