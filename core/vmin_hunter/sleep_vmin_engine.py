"""外供电睡眠电压（Sleep Vmin）探底引擎。

对应手动测试流程（External Supply 模式）：

1. 给芯片 Vcore 外供电，唤醒电压取最高值 ``wake_voltage``。
2. 通过 IIC 接口把芯片内部电源输出调到最低值（``init_internal_supply`` 回调），
   避免内部电源影响外部供电准确性；整个遍历开始前只执行一次。
2.5 保护逻辑：遍历开始前主动触发 STATUS 并读取 UART，确保 DUT 以 sleep=0
   （唤醒）这一已知状态进入测试；若读到 sleep=1 则再翻转一次回到 sleep=0。
3. 从高到低遍历睡眠 Vcore 电压 ``sleep_points``，每个睡眠电压点：
   a. 先在 ``wake_voltage`` 保持；
   b. 通过 STATUS IO 让芯片进入睡眠；
   c. 等待 ``pre_drop_delay_s``（默认 100ms）后，把 Vcore 降到当前睡眠电压；
   d. 保持 ``sleep_hold_s``（默认 3s）；
   e. 将 Vcore 恢复到 ``wake_voltage``；
   f. 通过 STATUS IO 让芯片唤醒。
4. 每个睡眠电压点完成后，在 ``wake_voltage`` 条件下用 STATUS IO 主动触发两次
   按键翻转（每次翻转状态），凑齐 sleep=0 / sleep=1 两种事件，配合
   ``AliveChecker`` 判断 DUT 是否正常。
   每个睡眠电压点会按 ``test_cnt`` 连续重复以上 a~f + 判活流程；任一次判活
   FAIL 即立即停止该电压点并判该点 FAIL，全部迭代 PASS 才算该点 PASS。
5. 最低的（全部迭代判活 PASS 的）睡眠电压即 Sleep Vmin。

本引擎与 UI / 具体仪器驱动解耦：所有硬件动作（设电压 / STATUS 睡眠 / STATUS
唤醒）由上层通过 ``EngineHooks`` 注入的同步回调执行；DUT 的 UART 日志由上层通过
``feed_uart_line`` 线程安全地喂入。引擎自身运行在 QThread（``run`` 为阻塞循环），
通过信号把日志与结果回填到 UI。
"""

import queue
import re
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

# 默认日志格式（旧 DUT 固件）：与 alive_checker.SleepWakeLogStrategy 默认一致。
# 实际匹配以注入的 strategy 为准（见 _read_sleep_state）。
_DEFAULT_WAKE_RE = re.compile(r"key_event_process:\s*sleep=0")
_DEFAULT_SLEEP_RE = re.compile(r"key_event_process:\s*sleep=1")


@dataclass
class SleepVminConfig:
    wake_voltage: float
    sleep_points: List[float]
    default_voltage: Optional[float] = None
    channel: int = 1
    current_limit: float = 1.0
    pre_drop_delay_s: float = 0.1
    sleep_hold_s: float = 3.0
    wake_settle_s: float = 0.1
    status_settle_s: float = 0.1
    alive_toggle_interval_s: float = 0.8
    alive_poll_interval_s: float = 0.05
    ensure_state_timeout_s: float = 3.0
    test_cnt: int = 1
    temperature: Optional[float] = None

    @property
    def restore_voltage(self) -> float:
        """睡眠点间恢复 / 初始唤醒使用的电压（Default 优先，回退到最高唤醒电压）。"""
        return self.default_voltage if self.default_voltage is not None else self.wake_voltage


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
    reset: Optional[Callable[[], None]] = None
    # 收尾时把 PWR/RESET/Status 控制 IO 释放为高阻，避免一直驱动 DUT
    release_pins: Optional[Callable[[], None]] = None


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
    result_row = Signal(float, object, str, str, str, str, str)
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
        # UART 重组缓冲：串口按字节块喂入，含 "| " 前缀的完整消息常跨多块，
        # 先累积再按 "数字/时间戳...| " 边界切分出完整消息行
        self._uart_reassembly = ""
        # 当前电压点收集到的精简标志日志（retention success/err、wake/sleep）
        self._point_flag_logs: List[str] = []

    # ------------------------------------------------------------------
    # 外部接口
    # ------------------------------------------------------------------
    def stop(self) -> None:
        self._stop_flag = True

    def feed_uart_line(self, line: str) -> None:
        if not line:
            return
        self._uart_queue.put(line)
        self._reassemble_and_collect(line)

    # 完整消息行起点："<num>/ <ts>/<level>/... | <msg>"（串口剥掉了 \n，
    # 故按此起点正则重组，而非依赖换行符）
    _MSG_LINE_RE = re.compile(r"\d+/\s*\d+/[A-Z]/[^|]*\|\s*.+")
    _MSG_START_RE = re.compile(r"(?=\d+/\s*\d+/[A-Z]/)")

    def _reassemble_and_collect(self, chunk: str) -> None:
        """累积字节块并按消息起点重组完整消息，收集精简标志日志。

        UI 喂入的块已被剥掉换行符，故按 "数字/时间戳/级别/" 的消息起点
        切分；含 "| " 的完整行命中后，仅保留关心的语义主体（retention
        success/err、sleep_pin_irqhandler 的 sleep=0/1），丢弃噪声。
        """
        self._uart_reassembly += chunk
        segs = self._MSG_START_RE.split(self._uart_reassembly)
        # 最后一段可能不完整，留待下次拼接
        self._uart_reassembly = segs.pop() if segs else ""
        for seg in segs:
            line = seg.strip()
            if not self._MSG_LINE_RE.match(line):
                continue
            flag = self._extract_flag(line)
            if flag is not None:
                self._point_flag_logs.append(flag)

    @staticmethod
    def _extract_flag(line: str) -> Optional[str]:
        """从完整消息行提取精简标志主体，不关心的行返回 None。"""
        body = line.split("|", 1)[-1].strip()
        if "retention check success" in body:
            return "retention check success"
        if "retention_check_data err" in body or "retention check err" in body:
            # 截断保留关键比对信息，丢弃后面冗长寄存器/栈转储
            return body[:80]
        if "sleep_pin_irqhandler" in body and ("sleep=0" in body or "sleep=1" in body):
            return body
        return None

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
            # 引擎异常崩溃也要把 CH 还原为 Default，避免停留在低压
            try:
                cfg = self._cfg
                self._hooks.set_voltage(cfg.channel, cfg.restore_voltage)
            except Exception:
                logger.error("Restore default voltage on crash failed",
                             exc_info=True)
            self._release_pins_safe()
            self.finished.emit(False, str(exc))

    def _run_sweep(self) -> None:
        cfg = self._cfg
        temp = cfg.temperature
        ch = cfg.channel

        restore_v = cfg.restore_voltage
        self.log_message.emit(
            f"[START] Sleep Vmin sweep: default={restore_v:.3f}V, "
            f"points={cfg.sleep_points}"
        )

        if self._hooks.reset is not None:
            self.log_message.emit("[INIT] Reset DUT before sweep")
            self._safe_hook("reset", self._hooks.reset)

        self._safe_hook("set_voltage", lambda: self._hooks.set_voltage(ch, restore_v))
        self._safe_hook("output_on", lambda: self._hooks.output_on(ch))
        time.sleep(cfg.wake_settle_s)

        if self._hooks.init_internal_supply is not None:
            self.log_message.emit(
                "[INIT] IIC: set chip internal supply to minimum"
            )
            messages = []

            def _do_init_supply():
                result = self._hooks.init_internal_supply()
                if result:
                    messages.extend(result)

            self._safe_hook("init_internal_supply", _do_init_supply)
            for msg in messages:
                self.log_message.emit(msg)
            time.sleep(cfg.wake_settle_s)

        if not self._ensure_wake_state():
            self._result.stopped = True
            self._finalize(None)
            return

        total = len(cfg.sleep_points)
        cnt = max(1, int(cfg.test_cnt))
        last_pass: Optional[float] = None

        for idx, sleep_v in enumerate(cfg.sleep_points):
            if self._stop_flag:
                self.log_message.emit("[STOP] Stopped by user.")
                self._result.stopped = True
                self._finalize(last_pass)
                return

            self.progress.emit(idx + 1, total)
            self.log_message.emit(
                f"[STEP {idx + 1}/{total}] Sleep voltage = {sleep_v:.3f} V "
                f"(x{cnt})"
            )

            point_status = "PASS"
            point_note = ""
            self._point_flag_logs = []
            pass_count = 0
            done = 0
            for it in range(1, cnt + 1):
                if self._stop_flag:
                    self.log_message.emit("[STOP] Stopped by user.")
                    self._result.stopped = True
                    self._emit_row(
                        sleep_v, temp, ch, f"{pass_count}/{done}",
                        point_status, "stopped during iterations",
                    )
                    self._finalize(last_pass)
                    return

                if cnt > 1:
                    self.log_message.emit(
                        f"[ITER {it}/{cnt}] Sleep voltage = {sleep_v:.3f} V"
                    )

                outcome = self._run_one_sleep_point(sleep_v)
                if isinstance(outcome, AliveChecker):
                    checker = outcome
                    status, note = self._run_alive_check(sleep_v, checker)
                elif isinstance(outcome, tuple):
                    # ("FAIL", note) / ("FAIL", note, flag)：序列或崩溃失败
                    status = outcome[0]
                    note = outcome[1] if len(outcome) > 1 else ""
                else:
                    status, note = "FAIL", "sleep/drop/restore sequence failed"

                done += 1
                if status == "PASS":
                    pass_count += 1
                else:
                    point_status, point_note = status, note
                    break

            # 去重保序：同一标志（如多次 retention success）只保留一条
            seen_flags = list(dict.fromkeys(self._point_flag_logs))
            self._emit_row(
                sleep_v, temp, ch, f"{pass_count}/{cnt}",
                point_status, point_note, " | ".join(seen_flags),
            )

            if point_status == "PASS":
                last_pass = sleep_v
                self._result.last_pass_voltage = sleep_v
            else:
                self._result.first_fail_voltage = sleep_v
                self.log_message.emit(
                    f"[FAIL] DUT abnormal at sleep={sleep_v:.3f} V ({point_note}); "
                    f"stop hunting."
                )
                break

        self._finalize(last_pass)

    # ------------------------------------------------------------------
    # 保护逻辑：探测前主动触发 STATUS，确保 DUT 以 sleep=0（唤醒）状态进入测试
    # ------------------------------------------------------------------
    def _ensure_wake_state(self) -> bool:
        cfg = self._cfg

        self.log_message.emit(
            "[INIT] Ensure DUT enters test in sleep=0 (wake) state"
        )

        for attempt in range(2):
            if self._stop_flag:
                self.log_message.emit("[STOP] Stopped by user.")
                return False

            self._drain_uart_queue()
            try:
                # 先反向再正向：唤醒电平=High 时 Low→High，确保即使 DUT 本已唤醒
                # 也能产生一次真实唤醒沿，从而等到 sleep=0 日志
                self.log_message.emit("[INIT] STATUS toggle (ensure wake: sleep->wake)")
                self._hooks.status_sleep()
                time.sleep(cfg.alive_toggle_interval_s)
                self._hooks.status_wake()
            except Exception as exc:
                logger.error("Ensure-wake trigger failed: %s", exc, exc_info=True)
                self.log_message.emit(f"[ERROR] Ensure-wake trigger failed: {exc}")
                return False

            state = self._read_sleep_state(cfg.ensure_state_timeout_s)
            if state == 0:
                self.log_message.emit("[INIT] DUT confirmed sleep=0 (wake).")
                return True
            if state == 1:
                self.log_message.emit(
                    "[INIT] DUT at sleep=1, toggle again to reach sleep=0."
                )
                if self._sleep_with_stop(cfg.alive_toggle_interval_s):
                    return False
                continue

            self.log_message.emit(
                f"[FAIL] No sleep state log within "
                f"{cfg.ensure_state_timeout_s:.1f}s while ensuring wake state."
            )
            return False

        self.log_message.emit(
            "[FAIL] Unable to put DUT into sleep=0 (wake) state before test."
        )
        return False

    def _read_sleep_state(self, timeout_s: float) -> Optional[int]:
        """在整个时间窗内监听 sleep 状态。

        反向沿(sleep)的 sleep=1 会先于正向沿(wake)的 sleep=0 到达；
        故见到 sleep=1 不立即返回，持续等到窗尾：优先确认 sleep=0，
        仅当整窗只见 sleep=1 才返回 1，均无则返回 None。
        """
        deadline = time.monotonic() + timeout_s
        saw_sleep = False
        while time.monotonic() < deadline:
            if self._stop_flag:
                return None
            try:
                line = self._uart_queue.get(
                    timeout=min(self._cfg.alive_poll_interval_s,
                                max(0.0, deadline - time.monotonic()))
                )
            except queue.Empty:
                continue
            logger.debug("DUT UART: %s", line)
            wake_re = getattr(self._strategy, "_wake_re", _DEFAULT_WAKE_RE)
            sleep_re = getattr(self._strategy, "_sleep_re", _DEFAULT_SLEEP_RE)
            alive_re = getattr(self._strategy, "_alive_re", None)
            if alive_re is not None and alive_re.search(line):
                return 0
            if wake_re.search(line):
                return 0
            if sleep_re.search(line):
                saw_sleep = True
        return 1 if saw_sleep else None

    # ------------------------------------------------------------------
    # 单个睡眠电压点的睡眠/降压/恢复/唤醒流程
    # 返回: 成功 → 唤醒沿启动的 AliveChecker（供 _run_alive_check 续用）；
    #       失败 → "FAIL" 字符串 / False
    # ------------------------------------------------------------------
    def _run_one_sleep_point(self, sleep_v: float):
        cfg = self._cfg
        ch = cfg.channel
        restore_v = cfg.restore_voltage
        try:
            self._hooks.set_voltage(ch, restore_v)
            time.sleep(cfg.wake_settle_s)

            self.log_message.emit("[SEQ] STATUS -> sleep")
            self._hooks.status_sleep()
            time.sleep(cfg.pre_drop_delay_s)

            self.log_message.emit(f"[SEQ] Drop Vcore -> {sleep_v:.3f} V (hold {cfg.sleep_hold_s:.1f}s)")
            self._hooks.set_voltage(ch, sleep_v)
            # 睡眠保持期持续监听 UART：崩溃/retention 错误立即判该点失败，
            # 避免崩溃日志滞留到判活阶段才被读出而无法归属到当前电压点
            crash_line = self._watch_uart_crash(cfg.sleep_hold_s)
            if crash_line is not None:
                self.log_message.emit(
                    f"[FAIL] DUT crash during sleep hold at {sleep_v:.3f} V: {crash_line}"
                )
                return "FAIL", f"crash during sleep hold: {crash_line}", crash_line
            if self._stop_flag:
                return False

            self.log_message.emit(f"[SEQ] Restore Vcore -> {restore_v:.3f} V")
            self._hooks.set_voltage(ch, restore_v)
            crash_line = self._watch_uart_crash(cfg.wake_settle_s)
            if crash_line is not None:
                self.log_message.emit(
                    f"[FAIL] DUT crash after restore at {sleep_v:.3f} V: {crash_line}"
                )
                return "FAIL", f"crash after restore: {crash_line}", crash_line
            if self._stop_flag:
                return False

            self.log_message.emit("[SEQ] STATUS -> wake")
            # 唤醒沿即判活起点：先启动判活会话再触发，避免漏掉紧随其后的 sleep=0 日志
            checker = AliveChecker(self._strategy)
            checker.start()
            self._hooks.status_wake()
            result = self._pump_uart_to_checker(checker, cfg.status_settle_s)
            if result.state is AliveState.FAIL:
                return "FAIL", f"{result.fail_reason.value}: {result.detail}"
            return checker
        except Exception as exc:
            logger.error("Sleep point %.3fV sequence failed: %s", sleep_v, exc, exc_info=True)
            self.log_message.emit(f"[ERROR] Sequence failed at {sleep_v:.3f} V: {exc}")
            return False

    def _pump_uart_to_checker(self, checker, duration_s: float):
        """在 duration_s 内把 UART 队列逐条喂给 checker，返回最新判活结果。

        用于唤醒沿之后的窗口期：既能把已到达/紧随的 sleep=0 日志计入判活，
        又能在窗口内尽早检出崩溃关键字。返回 PENDING 表示窗口内未凑齐判定。
        """
        cfg = self._cfg
        deadline = time.monotonic() + duration_s
        result = checker.result
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0 or self._stop_flag:
                return result
            try:
                line = self._uart_queue.get(
                    timeout=min(cfg.alive_poll_interval_s, remaining)
                )
            except queue.Empty:
                continue
            logger.debug("DUT UART: %s", line)
            result = checker.feed_line(line)
            if result.state is not AliveState.PENDING:
                return result

    # ------------------------------------------------------------------
    # 判活：沿用唤醒沿启动的判活会话，等待 DUT 上报唤醒事件（sleep=0）
    # ------------------------------------------------------------------
    def _run_alive_check(self, sleep_v: float, checker):
        cfg = self._cfg

        # 唤醒沿后的窗口期日志可能已使 checker 提前 PASS/FAIL
        result = checker.result
        if result.state is AliveState.PASS:
            return "PASS", result.detail
        if result.state is AliveState.FAIL:
            return "FAIL", f"{result.fail_reason.value}: {result.detail}"

        self.log_message.emit("[ALIVE] wait wake event (sleep=0)")
        while True:
            if self._stop_flag:
                return "FAIL", "stopped during alive check"

            try:
                line = self._uart_queue.get(timeout=cfg.alive_poll_interval_s)
            except queue.Empty:
                result = checker.tick()
            else:
                logger.debug("DUT UART: %s", line)
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

    def _watch_uart_crash(self, duration_s: float) -> Optional[str]:
        """在 duration_s 内监听 UART 队列，命中崩溃/retention 错误立即返回该行。

        读到的非崩溃行先暂存，窗口结束（或命中崩溃）时一次性回吐到队列，
        避免吞掉后续判活所需日志；用暂存而非即读即回，防止同一行在队尾
        被反复读出造成的忙等。返回 None 表示窗口内无崩溃（或收到停止请求）。
        """
        deadline = time.monotonic() + duration_s
        match_crash = getattr(self._strategy, "_match_crash", None)
        stash = []
        crash_line = None
        while time.monotonic() < deadline:
            if self._stop_flag:
                break
            try:
                line = self._uart_queue.get(
                    timeout=min(0.05, max(0.0, deadline - time.monotonic()))
                )
            except queue.Empty:
                continue
            logger.debug("DUT UART: %s", line)
            if match_crash is not None and match_crash(line) is not None:
                crash_line = line
                break
            stash.append(line)
        for line in stash:
            self._uart_queue.put(line)
        if crash_line is not None:
            # 崩溃行（含 ASSERT 的整条转储）按语义精简后纳入标志
            flag = self._extract_flag(crash_line)
            if flag is not None:
                self._point_flag_logs.append(flag)
            else:
                self._point_flag_logs.append(crash_line[:80])
        return crash_line

    def _safe_hook(self, name: str, fn: Callable[[], None]) -> None:
        try:
            fn()
        except Exception as exc:
            logger.error("Hook '%s' failed: %s", name, exc, exc_info=True)
            self.log_message.emit(f"[ERROR] Hook '{name}' failed: {exc}")
            raise

    def _release_pins_safe(self) -> None:
        """收尾把 PWR/RESET/Status IO 释放为高阻；未注入或失败仅记录，不阻断收尾。"""
        hook = getattr(self._hooks, "release_pins", None)
        if hook is None:
            return
        try:
            hook()
            self.log_message.emit("[FINISH] Release PWR/RESET/Status IO to High-Z")
        except Exception as exc:
            logger.error("Release pins to High-Z failed: %s", exc, exc_info=True)
            self.log_message.emit(f"[ERROR] Release pins to High-Z failed: {exc}")

    def _emit_row(self, sleep_v, temp, ch, pass_cnt, status, note,
                  flag_log="") -> None:
        self._result.rows.append({
            "voltage": sleep_v,
            "temperature": temp,
            "channel": ch,
            "pass_cnt": pass_cnt,
            "status": status,
            "note": note,
            "flag_log": flag_log,
        })
        self.result_row.emit(
            sleep_v, temp, f"CH{ch}", str(pass_cnt), status, note, flag_log
        )

    def _finalize(self, last_pass: Optional[float]) -> None:
        # 收尾（PASS/FAIL/异常/停止）统一把该 CH 还原为 Default 电压，
        # 避免停留在失败点低压导致 DUT 持续异常
        cfg = self._cfg
        try:
            restore_v = cfg.restore_voltage
            self._hooks.set_voltage(cfg.channel, restore_v)
            self.log_message.emit(
                f"[FINISH] Restore CH{cfg.channel} -> {restore_v:.3f} V (default)"
            )
        except Exception as exc:
            logger.error("Restore default voltage failed: %s", exc, exc_info=True)
            self.log_message.emit(f"[ERROR] Restore default voltage failed: {exc}")
        self._release_pins_safe()
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
