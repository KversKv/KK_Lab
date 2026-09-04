# -*- coding: utf-8 -*-
"""DSOX4034A 强制触发时基扫描封装（无触发源场景，禁固定 sleep）。

背景：LDO/DCDC 输出为 DC + 瞬态脉冲，无稳定边沿可供示波器真实触发；原
RUN/STOP + 固定 settle 流程等待时间长且不确定。本模块改用
「SINGLE 武装 + FORCe 强制触发 + 状态位完成判据」：
  - 等待时间由完成判据（OPER COND RUN 位清零）决定，不用 sleep 猜；
  - 唯一固定 sleep 是预触发微填充（REFerence=LEFT 时 ≈2ms，PRE≈0）；
  - 每时基点 VISA timeout 动态设置（1.3×T_expect+2.0s），用完恢复；
  - calibrate() 提供逐档 P95 标定查表，运行时以查表值兜底 timeout。

分层：本文件属 instruments/（纯 SCPI 封装，无 Qt），由 core/ 经 DSOX4034A
实例调用（组合复用其 write/query 底层）。
"""
from __future__ import annotations

import math
import time
from contextlib import contextmanager
from typing import Any, Iterator, Mapping, Sequence

from log_config import get_logger

logger = get_logger(__name__)

__all__ = ["DSOXFastCapture", "FastCaptureError", "FastCaptureTimeoutError"]


class FastCaptureError(Exception):
    """强制触发采集封装异常。"""


class FastCaptureTimeoutError(FastCaptureError):
    """完成判据超时（含一次重试后仍失败）。"""


class DSOXFastCapture:
    """Keysight InfiniiVision「改时基→满屏刷新→读测量值」快速封装。

    用法（真机）::

        scope = create_oscilloscope("dsox4034a", addr)
        fc = DSOXFastCapture(scope, measure_cmds=("VPP", "VAVerage"),
                             channels=(1,), acquire_points=100_000)
        fc.configure_once()                 # 循环外一次性配置
        for tb in [1e-3, 5e-3, 5e-2]:       # 从小到大
            fc.set_timebase_and_capture(tb)  # STOP→改时基→SINGLE→FORCe→判据等待
            vals = fc.read_measurements()    # 一条复合查询批量读值
    """

    # ---- 经验常数（T_FIXED 需 calibrate() 实测标定后覆盖 timeout 查表） ----
    T_FIXED = 0.06            # IO+重配置+渲染+测量 经验常数（秒）
    VISA_FACTOR = 1.3         # VISA timeout = VISA_FACTOR×T_expect + VISA_MARGIN
    VISA_MARGIN_S = 2.0
    # ---- 完成判据轮询参数（禁高频轮询：间隔=max(5ms, 0.02×10×TB)） ----
    POLL_MIN_S = 0.005
    POLL_SPAN_RATIO = 0.02    # × 一屏(10×TB)
    OPER_RUN_BIT = 3          # OPERation:CONDition 寄存器 RUN 位（采集中=1）
    OPER_FAIL_FALLBACK = 3    # OPER 解析连续失败 N 次后回退 :RSTate? 判据
    # ---- 无效测量值标记阈值（Keysight 惯例无效值 9.9E+37） ----
    INVALID_THRESHOLD = 9.0e36
    # ---- 标定参数 ----
    CAL_ROUNDS = 20           # 每档默认标定轮数
    CAL_P95_K = 1.2           # 查表值 = P95 × 1.2

    # 预触发占比（REFerence 位置决定）：LEFT→触发点贴最左，PRE≈0
    _PRE_RATIO = {"LEFT": 0.0, "CENT": 0.5, "CENTer": 0.5, "RIGH": 1.0, "RIGHT": 1.0}

    def __init__(
        self,
        scope: Any,
        measure_cmds: Sequence[str] = ("VPP", "VAVerage"),
        channels: Sequence[int] = (1,),
        acquire_points: int = 10_000,
        reference: str = "LEFT",
        timeout_table: Mapping[float, float] | None = None,
    ):
        """Args:
            scope: 已连接的 DSOX4034A 实例（复用其 write/query/instrument）；
            measure_cmds: 批量读值的测量量名（如 VPP/VAVerage/VMAX/VMIN）；
            channels: 参与测量/保留显示的模拟通道（其余通道关显示）；
            acquire_points: 存储深度「够用的最小值」——限制点数以压缩重配置
                与处理时间；瞬态类测试需按沿宽选足够点数（如 100k）；
            reference: 时间参考点（LEFT/CENTer/RIGH），默认 LEFT（见
                configure_once 注释）；
            timeout_table: calibrate() 产出的 {TB: timeout} 查表（可后补）。
        """
        self._scope = scope
        self._measure_cmds = tuple(measure_cmds) or ("VPP",)
        self._channels = tuple(sorted({int(c) for c in channels})) or (1,)
        self._acquire_points = int(acquire_points)
        self._reference = str(reference)
        key = str(reference).upper()
        # 兼容长短写法：LEFT/RIGHT/CENT/CENTer 均按 4 字符前缀归一
        self._pre_ratio = self._PRE_RATIO.get(
            key, self._PRE_RATIO.get(key[:4], 0.0))
        self.timeout_table: dict[float, float] = dict(timeout_table or {})
        self.last_invalid: list[str] = []   # read_measurements 的无效值键名
        self._oper_fail_streak = 0

    # ------------------------------------------------------------------
    # 1) 循环外一次性配置
    # ------------------------------------------------------------------

    def configure_once(self) -> None:
        """循环外一次性配置（只发一次）。

        顺序理由：
        - HEADer OFF：响应去命令头，解析统一为裸数字；
        - ACQuire:TYPE NORMal：关平均/高分辨等多次采集模式，一次触发即一屏；
        - TIMebase:MODE MAIN：禁 Roll——大时基下 Roll 连续滚动采集，
          永无「一屏采完」态，完成判据永不满足；
        - TIMebase:REFerence LEFT：**关键**——把触发参考点压到屏幕最左，
          预触发占比 PRE≈0，SINGLE 武装后立即可 FORCe 出触发；若为
          CENTer/RIGHT，须先填半屏/满屏预触发缓冲才接受触发，等待不可控；
        - TRIGger:SWEep NORMal：关 Auto——Auto 在无触发若干 ms 后自动出
          触发（旧帧/不确定时刻）；NORMal 只认真实或 FORCe 触发，波形确定；
        - MEASure:STATistics OFF：关统计，读值即时有效，不依赖统计收敛；
        - ACQuire:POINts 最小值：限制存储深度，压缩改时基后的重配置与
          波形处理时间；
        - 关未用通道/Math/FFT：减少渲染与测量处理开销。
        注意：本方法改变仪器全局状态（HEADer/统计等），不复位恢复。
        """
        cmds = [
            ':SYSTem:HEADer OFF',
            ':ACQuire:TYPE NORMal',
            ':TIMebase:MODE MAIN',
            f':TIMebase:REFerence {self._reference}',
            ':TRIGger:SWEep NORMal',
            ':MEASure:STATistics OFF',
            f':ACQuire:POINts {self._acquire_points}',
        ]
        for cmd in cmds:
            self._scope.write(cmd)
        # 关未用模拟通道显示（保留本封装要用的通道）
        for ch in (1, 2, 3, 4):
            if ch in self._channels:
                self._scope.write(f':CHANnel{ch}:DISPlay ON')
            else:
                self._scope.write(f':CHANnel{ch}:DISPlay OFF')
        # 关 Math / FFT 显示（部分固件命令子集不同，best-effort 不阻断）
        for cmd in (':FUNCtion:DISPlay OFF', ':FFT:DISPlay OFF'):
            try:
                self._scope.write(cmd)
            except Exception:  # noqa: BLE001
                logger.debug('configure_once %s 失败（best-effort）', cmd,
                             exc_info=True)
        # 确认整批配置生效
        self._scope.query('*OPC?')
        logger.info('DSOXFastCapture 一次性配置完成: channels=%s points=%d '
                    'reference=%s', self._channels, self._acquire_points,
                    self._reference)

    # ------------------------------------------------------------------
    # 2) 单时基点：STOP → 改时基 → *OPC? → SINGLE → 预填 → FORCe → 判据等待
    # ------------------------------------------------------------------

    def set_timebase_and_capture(self, tb: float) -> float:
        """单时基点采集（顺序不可颠倒，见 _capture_once 注释）。

        Returns:
            本点实际耗时（发出 :STOP → 完成判据满足，秒）。

        Raises:
            FastCaptureTimeoutError: 判据超时且重试 1 次仍失败。
        """
        timeout = self._timeout_for(tb)
        started = time.monotonic()
        try:
            with self._visa_timeout(timeout):
                self._capture_once(tb, timeout)
        except FastCaptureTimeoutError as e:
            # 异常处理：timeout 后重试 1 次并记录日志
            logger.warning('DSOXFastCapture tb=%g 判据超时(%.2fs)，重试 1 次: %s',
                           tb, timeout, e)
            with self._visa_timeout(timeout):
                self._capture_once(tb, timeout)   # 再失败直接上抛
        return time.monotonic() - started

    def _capture_once(self, tb: float, timeout: float) -> None:
        inst = self._scope.instrument
        if inst is None:
            raise FastCaptureError('示波器未连接')

        # a. 先 :STOP 再改时基：改时基会使仪器丢弃当前屏并重新采集整屏；
        #    若在 RUN 态改时基，还得先把「旧时基的一屏」采完才轮到新配置
        #    生效（等于白等一屏无效采集）。先 STOP 进入确定停态，改时基
        #    立即生效，无无效等待。
        self._scope.write(':STOP')

        # b. 改时基
        self._scope.write(f':TIMebase:SCALe {tb}')

        # c. *OPC? 确认配置生效后再武装，防止 SINGLE 沿用旧时基
        self._scope.query('*OPC?')

        # d. 武装单次采集（SWEep NORMal 下仪器不会自动触发旧帧）
        self._scope.write(':SINGle')

        # e. 预触发填充：REFerence=LEFT → PRE≈0，仅需微填充（≈2ms）；
        #    若 reference 为 CENTer/RIGHT，则须先填 SPAN×PRE 才能接受触发
        span = 10.0 * tb                      # 一屏物理时间，不可压缩
        pre = max(0.002, span * self._pre_ratio)
        time.sleep(pre)

        # f. 强制触发（无触发源场景唯一确定手段；:FORCe 失败回退 *TRG）
        self._force_trigger()

        # g. 阻塞等待采集完成：轮询 OPER COND RUN 位清零（SINGLE 采完自动
        #    停），间隔 = max(5ms, 0.02×10×TB)，整体受 timeout 保护
        if not self._wait_acq_done(tb, timeout):
            raise FastCaptureTimeoutError(
                f'完成判据超时: tb={tb:g}s, timeout={timeout:.2f}s')

    def _force_trigger(self) -> None:
        """发强制触发；:FORCe 异常时回退 IEEE 488.2 *TRG（等价语义）。"""
        try:
            self._scope.write(':FORCe')
        except Exception:  # noqa: BLE001 - 部分 IO 栈对 :FORCe 无响应回退
            logger.warning(':FORCe 发送失败，回退 *TRG', exc_info=True)
            self._scope.write('*TRG')

    def _wait_acq_done(self, tb: float, timeout: float) -> bool:
        """完成判据：OPER COND RUN 位清零（=1 采集中，=0 已停止/采完）。

        OPER 查询连续异常时回退 :RSTate?（STOP 即完成），整体受 timeout
        兜底；轮询间隔 max(5ms, 0.02×一屏)，禁高频轮询。
        """
        interval = max(self.POLL_MIN_S, self.POLL_SPAN_RATIO * 10.0 * tb)
        deadline = time.monotonic() + timeout
        while True:
            done = self._check_done_oper()
            if done is not None:
                self._oper_fail_streak = 0
                if done:
                    return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(interval)

    def _check_done_oper(self) -> bool | None:
        """读 OPERation:CONDition? RUN 位。

        Returns:
            True=已停止(采集完成) / False=采集中 / None=查询失败（回退判据）。
        """
        try:
            cond = int(float(self._scope.query(':OPERegister:CONDition?')))
            return (cond & (1 << self.OPER_RUN_BIT)) == 0
        except (ValueError, TypeError) as e:
            self._oper_fail_streak += 1
            logger.debug('OPER COND 解析失败(连续 %d 次): %s',
                         self._oper_fail_streak, e)
            if self._oper_fail_streak >= self.OPER_FAIL_FALLBACK:
                # 回退判据：:RSTate?（驱动 is_acquiring 同款，已真机验证）
                try:
                    state = self._scope.query(':RSTate?').strip().upper()
                    return state not in ('RUN', 'SING', 'WAIT')
                except Exception:  # noqa: BLE001
                    logger.debug('RSTate 回退查询失败', exc_info=True)
            return None

    # ------------------------------------------------------------------
    # 3) 批量读测量值（一条复合查询）
    # ------------------------------------------------------------------

    def read_measurements(self) -> dict[str, float | None]:
        """一条复合查询批量读值：:MEASure:VPP? CHAN1;:MEASure:VAVerage? CHAN1...

        采集已完成（stop 定格帧）时读值即时有效（STATistics OFF）。
        无效值（|v|>9.9E+37 阈值）置 None 并标记到 self.last_invalid。
        调用前须先 set_timebase_and_capture 成功。
        """
        self.last_invalid = []
        queries = [f':MEASure:{m}? CHANnel{ch}'
                   for ch in self._channels for m in self._measure_cmds]
        # 一条复合查询（';' 连接）批量发出，逐条读回等数响应
        self._scope.write(';'.join(queries))
        values: dict[str, float | None] = {}
        try:
            raws = [self._scope.read() for _ in queries]
        except Exception as e:  # noqa: BLE001
            raise FastCaptureError(f'批量测量读回失败: {e}') from e
        for (ch, m), raw in zip(
                ((ch, m) for ch in self._channels for m in self._measure_cmds),
                raws):
            key = f'CH{ch}:{m}'
            try:
                v = float(raw)
            except ValueError:
                values[key] = None
                self.last_invalid.append(key)
                logger.warning('测量值无法解析: %s=%r', key, raw)
                continue
            if abs(v) > self.INVALID_THRESHOLD:
                # 9.9E+37 为 Keysight 无效测量值（无有效样本等），标记无效
                values[key] = None
                self.last_invalid.append(key)
                logger.warning('测量值无效(%.3g): %s', v, key)
            else:
                values[key] = v
        return values

    # ------------------------------------------------------------------
    # 4) 标定
    # ------------------------------------------------------------------

    def calibrate(self, timebases: Sequence[float],
                  rounds: int = CAL_ROUNDS) -> dict[float, float]:
        """逐档标定 timeout 查表：各时基档跑 N 次，取 P95×1.2 存表。

        记录 (发出 :STOP → 完成判据满足) 的实际耗时；运行时用查表值做
        timeout，实际等待仍由完成判据决定（查表仅兜底，不会引入固定 sleep）。
        标定前须先 configure_once()；标定失败的轮次跳过、全失败则该档
        不入表（运行时回公式）。
        """
        table: dict[float, float] = {}
        for tb in sorted(set(float(t) for t in timebases)):  # 从小到大
            samples: list[float] = []
            for i in range(rounds):
                t0 = time.monotonic()
                try:
                    self.set_timebase_and_capture(tb)
                    samples.append(time.monotonic() - t0)
                except FastCaptureError:
                    logger.warning('标定失败 tb=%g 第 %d/%d 轮，跳过',
                                   tb, i + 1, rounds)
            if samples:
                table[tb] = self._p95(samples) * self.CAL_P95_K
                logger.info('标定 tb=%g: P95×%.1f=%.3fs (n=%d, max=%.3fs)',
                            tb, self.CAL_P95_K, table[tb], len(samples),
                            max(samples))
            else:
                logger.error('标定 tb=%g 全部失败，运行时回公式', tb)
        self.timeout_table.update(table)
        return dict(self.timeout_table)

    # ------------------------------------------------------------------
    # 便捷入口：按时基从小到大执行整轮扫描
    # ------------------------------------------------------------------

    def run_sweep(self, timebases: Sequence[float]) -> list[dict[str, Any]]:
        """测试点按时基从小到大排序执行：每档 capture + 批量读值。"""
        results: list[dict[str, Any]] = []
        for tb in sorted(set(float(t) for t in timebases)):  # 从小到大
            elapsed = self.set_timebase_and_capture(tb)
            values = self.read_measurements()
            results.append({
                'timebase_s': tb,
                'elapsed_s': round(elapsed, 4),
                'values': values,
                'invalid': list(self.last_invalid),
            })
        return results

    # ------------------------------------------------------------------
    # 内部：timeout 计算 / VISA 动态超时
    # ------------------------------------------------------------------

    def _timeout_for(self, tb: float) -> float:
        """timeout = 查表值（标定）或 1.3×T_expect+2.0（公式）。

        T_expect = T_pre + T_post + T_fixed
                 = SPAN×PRE + SPAN×(1-PRE) + T_fixed = SPAN + T_fixed
        REFerence=LEFT 时 PRE≈0 → T_pre≈0.002s、T_post≈一屏（不可压缩）。
        """
        hit = self.timeout_table.get(float(tb))
        if hit is not None:
            return float(hit)
        span = 10.0 * tb
        pre = max(0.002, span * self._pre_ratio)
        t_post = span * (1.0 - self._pre_ratio)
        t_expect = pre + t_post + self.T_FIXED
        return self.VISA_FACTOR * t_expect + self.VISA_MARGIN_S

    @contextmanager
    def _visa_timeout(self, timeout_s: float) -> Iterator[None]:
        """每个时基点动态设置 VISA timeout，用完恢复原值。"""
        inst = getattr(self._scope, 'instrument', None)
        if inst is None:
            raise FastCaptureError('示波器未连接')
        old_ms = inst.timeout
        inst.timeout = int(timeout_s * 1000.0)
        try:
            yield
        finally:
            inst.timeout = old_ms

    @staticmethod
    def _p95(samples: Sequence[float]) -> float:
        """P95：排序取 ceil(0.95×n)-1 位（保守向上取整）。"""
        s = sorted(samples)
        k = max(0, math.ceil(0.95 * len(s)) - 1)
        return s[k]
