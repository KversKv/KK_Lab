# -*- coding: utf-8 -*-
"""Output Voltage 测试 Worker 与旧接口运行器（仅依赖 QtCore）。"""

import threading
import time

from PySide6.QtCore import QObject, QThread, Signal

from instruments.mock.mock_instruments import MockI2C, MockIT2705, MockN6705C
from lib.i2c.i2c_interface_x64 import I2CInterface
from log_config import get_logger

from .output_voltage_analysis import (
    _PRECHECK_POINTS,
    _TAIL_STOP_POINTS,
    _TAIL_STOP_SPAN,
    build_result,
    compute_valid_range,
    precheck_first_points,
    validate_code_range,
)

_logger = get_logger(__name__)

_CC_LOAD_CURRENT_A = 0.001


class OutputVoltageWorker(QObject):
    log_message = Signal(str)
    chart_point = Signal(float, float)
    chart_clear = Signal()
    result_update = Signal(dict)
    test_finished = Signal(bool, str)
    # 前置校验失败 / 尾部饱和 → 请求 UI 弹窗让用户决定是否继续
    # （部分场景前几 bit 固有异常 / 需要完整曲线确认全程平坦）
    confirm_request = Signal(str, str)

    def __init__(
            self, n6705c, config, debug_flag=False, *,
            i2c_factory=None, mock_i2c_factory=None, time_module=None):
        super().__init__()
        self._n6705c = n6705c
        self._cfg = config
        self._debug = debug_flag
        self._stop_flag = False
        self._confirm_reply = threading.Event()
        self._confirm_continue = False
        self._saturation_continue = False
        self._i2c_factory = I2CInterface if i2c_factory is None else i2c_factory
        self._mock_i2c_factory = MockI2C if mock_i2c_factory is None else mock_i2c_factory
        self._time = time if time_module is None else time_module

    def request_stop(self):
        self._stop_flag = True

    def respond_confirm(self, continue_test):
        """UI 弹窗应答：是否继续扫描。"""
        self._confirm_continue = bool(continue_test)
        self._confirm_reply.set()

    def _wait_user_confirm(self, title, message):
        """请求 UI 弹窗确认并阻塞等待应答（期间可响应停止请求）。

        返回 (是否已应答, 是否继续)：等待期间用户停止时返回 (False, False)。
        """
        self._confirm_reply.clear()
        self._confirm_continue = False
        self.confirm_request.emit(title, message)
        while not self._confirm_reply.wait(0.1):
            if self._stop_flag:
                return False, False
        return True, self._confirm_continue

    def run(self):
        restore_ctx = None  # (i2c, device_addr, reg_addr, default_reg, width_flag)
        close_channel_ch = None
        success = False
        finish_reason = "测试未完成"
        try:
            device_addr = int(self._cfg["device_addr"], 16)
            reg_addr = int(self._cfg["reg_addr"], 16)
            msb = self._cfg["msb"]
            lsb = self._cfg["lsb"]
            width_flag = int(self._cfg["width_flag"])
            min_code = int(self._cfg["min_code"], 16)
            max_code = int(self._cfg["max_code"], 16)
            vmeter_ch = int(self._cfg["vmeter_channel"].replace("CH ", ""))
            vmeter_mode = self._cfg.get("vmeter_mode", "VMETer")
            validate_code_range(msb, lsb, min_code, max_code)
            if self._cfg.get("close_channel_after", False):
                close_channel_ch = vmeter_ch

            if self._debug:
                i2c = self._mock_i2c_factory()
                self.log_message.emit("[DEBUG] Using Mock I2C interface.")
            else:
                i2c = self._i2c_factory()

            if vmeter_mode == "CCLoad":
                self._n6705c.channel_off(vmeter_ch)
                self._n6705c.set_mode(vmeter_ch, "CCLoad")
                self._n6705c.set_current(vmeter_ch, -_CC_LOAD_CURRENT_A)
                self._n6705c.channel_on(vmeter_ch)
                self.log_message.emit(f"[TEST] CH{vmeter_ch}=CCLoad, load current=1mA")
            else:
                self._n6705c.set_mode(vmeter_ch, "VMETer")
                self._n6705c.channel_on(vmeter_ch)
                self.log_message.emit(f"[TEST] CH{vmeter_ch}=VMETer (voltage only), channel ON")

            bit_count = msb - lsb + 1
            mask = (1 << bit_count) - 1

            default_reg = i2c.read(device_addr, reg_addr, width_flag)
            data_base = default_reg & (~(mask << lsb))

            max_code = min(max_code, mask)
            min_code = max(min_code, 0)

            total_points = max_code - min_code + 1
            if total_points <= 0:
                self.log_message.emit("[ERROR] Invalid code range (min > max).")
                finish_reason = "无效的代码范围"
                return

            # 前置校验点数：DEBUG_MOCK 电压为常数+噪声、单点无法判断变化，均跳过
            if self._debug or total_points < 2:
                precheck_n = 0
            else:
                precheck_n = min(_PRECHECK_POINTS, total_points)

            self.log_message.emit(f"[TEST] Device=0x{device_addr:02X}, Reg=0x{reg_addr:04X}, "
                                  f"MSB={msb}, LSB={lsb}, WidthFlag={width_flag}")
            self.log_message.emit(f"[TEST] Code range: 0x{min_code:X} ~ 0x{max_code:X} ({total_points} points)")

            hex_width = len(f"{max_code:X}")
            # 10进制位宽与16进制位宽均按 max_code 钉死，保证逐行对齐便于解析
            dec_width = len(str(max_code))

            self.chart_clear.emit()

            sleep_time = 0.0 if self._debug else 0.05

            default_voltage = self._n6705c.measure_voltage(vmeter_ch)
            default_code = (default_reg >> lsb) & mask
            self.log_message.emit(f"[TEST] Default voltage: {default_voltage:.4f}V (0x{default_code:X})")

            voltages = []
            codes = []
            precheck_failed = False
            precheck_asked = False

            settle_start = self._time.time()
            # 首次改写寄存器前记录恢复上下文：停止/异常路径也在 finally 兜底恢复默认值
            restore_ctx = (i2c, device_addr, reg_addr, default_reg, width_flag)
            write_reg = data_base | (min_code << lsb)
            i2c.write(device_addr, reg_addr, write_reg, width_flag)
            self.log_message.emit(f"[TEST] Setting min_code=0x{min_code:X}, waiting for output to stabilize...")

            recent_voltages = []
            while True:
                if self._stop_flag:
                    self.log_message.emit("[TEST] Stopped by user during stabilization.")
                    finish_reason = "测试被中止"
                    return
                v = self._n6705c.measure_voltage(vmeter_ch)
                recent_voltages.append(v)
                if len(recent_voltages) >= 3:
                    last3 = recent_voltages[-3:]
                    if (max(last3) - min(last3)) <= 0.005:
                        break
                self._time.sleep(sleep_time)

            self._time.sleep(0.1)
            settle_elapsed_ms = (self._time.time() - settle_start) * 1000.0
            self.log_message.emit(f"[TEST] Wait for mincode output cose: {settle_elapsed_ms:.0f}ms")

            # 表格化 MEAS 输出：Tab 分隔的 CSV 风格，方便复制后直接按列解析
            self.log_message.emit(
                f"[TEST] Code(Dec)\tCode(Hex)\tVoltage (V)\tΔ (mV)"
            )

            code = min_code
            while code <= max_code:
                if self._stop_flag:
                    self.log_message.emit("[TEST] Stopped by user.")
                    break

                write_reg = data_base | (code << lsb)
                i2c.write(device_addr, reg_addr, write_reg, width_flag)
                self._time.sleep(sleep_time)

                if self._debug and isinstance(self._n6705c, (MockN6705C, MockIT2705)):
                    self._n6705c._last_expected_v = 1.0

                measured_v = self._n6705c.measure_voltage(vmeter_ch)

                voltages.append(measured_v)
                codes.append(code)

                self.chart_point.emit(float(code), measured_v)

                # 首点无前值可差，差值列留空；注意 voltages 已含当前点，前值取 voltages[-2]
                if len(voltages) >= 2:
                    delta_mv = (measured_v - voltages[-2]) * 1000.0
                    delta_str = f"{delta_mv:+.1f}"
                else:
                    delta_str = ""
                self.log_message.emit(
                    f"[MEAS] {code}\t0x{code:0{hex_width}X}\t"
                    f"{measured_v:.4f}\t{delta_str}"
                )

                # 前置校验：前 N 点电压无变化或读数异常时弹窗交由用户决定是否继续
                # （部分场景前几 bit 固有异常）；仅询问一次，继续时剔除已测异常点
                if precheck_n and len(voltages) == precheck_n and not precheck_asked:
                    precheck_asked = True
                    ok, reason = precheck_first_points(voltages)
                    if not ok:
                        self.log_message.emit(
                            f"[WARN] Pre-check failed on first {precheck_n} points: {reason}"
                        )
                        _logger.warning("Output voltage pre-check failed: %s", reason)
                        answered, do_continue = self._wait_user_confirm(
                            "前置校验失败",
                            f"前 {precheck_n} 个测量点校验失败：\n\n{reason}\n\n"
                            "是否继续扫描？\n"
                            "（继续时已测异常点将被剔除，不参与性能指标计算）",
                        )
                        if not answered:
                            self.log_message.emit(
                                "[TEST] Stopped by user during pre-check confirmation."
                            )
                            precheck_failed = True
                            break
                        if not do_continue:
                            self.log_message.emit(
                                "[WARN] Test aborted by user. Check device addr / reg / bit-field "
                                "config and output enable, or raise Min Code above the dead-band region."
                            )
                            precheck_failed = True
                            break
                        # 用户选择继续：剔除已测异常前缀，性能指标计算自动排除
                        prefix_voltages = list(voltages)
                        prefix_codes = list(codes)
                        voltages.clear()
                        codes.clear()
                        self.log_message.emit(
                            f"[TEST] Continuing per user choice: first {precheck_n} abnormal "
                            "points excluded from performance metrics."
                        )
                        # 弹窗日志打断了 MEAS 表格，重印表头并复述已测点，保证表格连续可解析
                        self.log_message.emit(
                            f"[TEST] Code(Dec)\tCode(Hex)\tVoltage (V)\tΔ (mV)"
                        )
                        for j, (p_code, p_v) in enumerate(zip(prefix_codes, prefix_voltages)):
                            if j >= 1:
                                p_delta = f"{(p_v - prefix_voltages[j - 1]) * 1000.0:+.1f}"
                            else:
                                p_delta = ""
                            self.log_message.emit(
                                f"[MEAS] {p_code}\t0x{p_code:0{hex_width}X}\t"
                                f"{p_v:.4f}\t{p_delta}"
                            )

                # 尾部饱和检测：连续 N 点电压极差低于阈值（如受限于前级电压卡住）时弹窗
                # 交由用户决定是否继续；用户继续后本次运行不再触发
                # DEBUG_MOCK 电压为常数+噪声，必然触发，跳过
                if (not self._debug
                        and not self._saturation_continue
                        and len(voltages) >= _TAIL_STOP_POINTS
                        and (max(voltages[-_TAIL_STOP_POINTS:]) - min(voltages[-_TAIL_STOP_POINTS:]))
                        <= _TAIL_STOP_SPAN):
                    sat_v = voltages[-1]
                    self.log_message.emit(
                        f"[WARN] Output saturated at ~{sat_v:.4f}V for {_TAIL_STOP_POINTS} consecutive "
                        f"codes (code=0x{code:0{hex_width}X})."
                    )
                    _logger.warning(
                        "Output voltage saturated at %.4fV (code=0x%X)",
                        sat_v, code,
                    )
                    answered, do_continue = self._wait_user_confirm(
                        "输出饱和确认",
                        f"连续 {_TAIL_STOP_POINTS} 个代码点的电压极差 ≤ {_TAIL_STOP_SPAN * 1000:.0f}mV，"
                        f"疑似输出饱和：\n\n当前电压 ≈ {sat_v:.4f}V（code=0x{code:0{hex_width}X}）\n\n"
                        "是否继续扫描剩余代码点？\n"
                        "（继续时本次运行不再触发饱和终止，平坦段不参与性能指标计算）",
                    )
                    if not answered:
                        self.log_message.emit(
                            "[TEST] Stopped by user during saturation confirmation."
                        )
                        break
                    if not do_continue:
                        # 截断饱和平台：丢弃触发的 N 点平坦窗口，最大值取饱和前一个点
                        # （不回溯扩展——步进幅值接近阈值时回溯会误吞线性段末端点）
                        p = len(voltages) - _TAIL_STOP_POINTS
                        if p > 0:
                            voltages = voltages[:p]
                            codes = codes[:p]
                            self.log_message.emit(
                                f"[TEST] Saturation plateau trimmed: max voltage taken from "
                                f"code=0x{codes[-1]:0{hex_width}X} ({voltages[-1]:.4f}V), "
                                f"{len(voltages)} effective points kept."
                            )
                            self.result_update.emit(
                                build_result(voltages, codes, default_voltage, default_code, 100)
                            )
                        break
                    # 用户选择继续：本次运行不再触发饱和终止，保留平坦点（有效区间算法自动剔除）
                    self._saturation_continue = True
                    self.log_message.emit(
                        "[TEST] Continuing per user choice: saturation early-stop disabled "
                        "for this run."
                    )

                idx = code - min_code
                progress = int((idx + 1) / total_points * 100)

                self.result_update.emit(
                    build_result(voltages, codes, default_voltage, default_code, progress)
                )
                code += 1

            scan_completed = code > max_code
            if (len(voltages) >= 2 and scan_completed
                    and not self._stop_flag and not precheck_failed):
                low_valid, high_valid = compute_valid_range(voltages)

                if high_valid > low_valid:
                    self.log_message.emit(
                        f"[TEST] Valid code range: 0x{codes[low_valid]:0{hex_width}X} ~ "
                        f"0x{codes[high_valid]:0{hex_width}X} "
                        f"({codes[high_valid] - codes[low_valid] + 1} effective points out of {len(voltages)} total)"
                    )

                # 汇总日志：键按最长的 Default(0x..) 对齐，Step 取有效区间平均步进（与结果卡片一致）
                sum_pad = len(f"Default(0x{'F' * hex_width})")
                self.log_message.emit(f"[TEST] {'Reg Addr':<{sum_pad}} = 0x{reg_addr:04X}")
                self.log_message.emit(f"[TEST] {'MSB':<{sum_pad}} = {msb}")
                self.log_message.emit(f"[TEST] {'LSB':<{sum_pad}} = {lsb}")
                self.log_message.emit(
                    f"[TEST] {f'Min(0x{codes[low_valid]:0{hex_width}X})':<{sum_pad}} = {voltages[low_valid]:.4f}V"
                )
                self.log_message.emit(
                    f"[TEST] {f'Max(0x{codes[high_valid]:0{hex_width}X})':<{sum_pad}} = {voltages[high_valid]:.4f}V"
                )
                self.log_message.emit(
                    f"[TEST] {f'Default(0x{default_code:0{hex_width}X})':<{sum_pad}} = {default_voltage:.4f}V"
                )
                valid_voltages = voltages[low_valid:high_valid + 1]
                if len(valid_voltages) >= 2:
                    step_mv = (valid_voltages[-1] - valid_voltages[0]) / (len(valid_voltages) - 1) * 1000.0
                    self.log_message.emit(f"[TEST] {'Step':<{sum_pad}} = {step_mv:.4f}mV")
                    self.log_message.emit(
                        f"[TEST] {'Step Range':<{sum_pad}} = "
                        f"0x{codes[low_valid]:0{hex_width}X} ~ 0x{codes[high_valid]:0{hex_width}X} "
                        f"({valid_voltages[0]:.4f}V ~ {valid_voltages[-1]:.4f}V, "
                        f"{len(valid_voltages)} points)"
                    )

            if self._stop_flag or not scan_completed or precheck_failed:
                finish_reason = "测试被中止"
            elif not voltages:
                finish_reason = "未采集到测量数据"
            else:
                success = True
                finish_reason = "测试完成"

        except Exception as e:
            finish_reason = f"测试失败：{e}"
            self.log_message.emit(f"[ERROR] Test failed: {e}")
            _logger.error("Output voltage test failed", exc_info=True)
        finally:
            if close_channel_ch is not None:
                try:
                    self._n6705c.channel_off(close_channel_ch)
                    self.log_message.emit(f"[TEST] CH{close_channel_ch} turned off after test.")
                except Exception as e:
                    success = False
                    finish_reason = f"测试失败：关闭通道失败（{e}）"
                    self.log_message.emit(f"[ERROR] Failed to turn off channel: {e}")
                    _logger.error("Failed to turn off channel", exc_info=True)
            # 兜底恢复寄存器默认值：覆盖正常完成 / 用户停止 / 异常全部路径
            if restore_ctx is not None:
                try:
                    i2c, dev, reg, reg_default, wflag = restore_ctx
                    i2c.write(dev, reg, reg_default, wflag)
                    self.log_message.emit("[TEST] Register restored to default value.")
                except Exception as e:
                    success = False
                    finish_reason = f"测试失败：恢复寄存器失败（{e}）"
                    self.log_message.emit(f"[ERROR] Failed to restore register default value: {e}")
                    _logger.error("Failed to restore register default value", exc_info=True)
            self.test_finished.emit(success, finish_reason)


class OutputVoltageTestThread(QObject):
    """保留旧 start/run 接口的 QObject 运行器，业务由 OutputVoltageWorker 执行。"""

    log_message = Signal(str)
    chart_point = Signal(float, float)
    chart_clear = Signal()
    result_update = Signal(dict)
    test_finished = Signal(bool, str)
    confirm_request = Signal(str, str)

    _compute_valid_range = staticmethod(compute_valid_range)
    _build_result = staticmethod(build_result)
    _precheck_first_points = staticmethod(precheck_first_points)

    def __init__(
            self, n6705c, config, debug_flag=False, *,
            i2c_factory=None, mock_i2c_factory=None, time_module=None):
        super().__init__()
        self._thread = None
        self._worker = OutputVoltageWorker(
            n6705c, config, debug_flag,
            i2c_factory=i2c_factory,
            mock_i2c_factory=mock_i2c_factory,
            time_module=time_module,
        )
        self._worker.log_message.connect(self.log_message.emit)
        self._worker.chart_point.connect(self.chart_point.emit)
        self._worker.chart_clear.connect(self.chart_clear.emit)
        self._worker.result_update.connect(self.result_update.emit)
        self._worker.test_finished.connect(self.test_finished.emit)
        self._worker.confirm_request.connect(self.confirm_request.emit)

    def start(self):
        if self._thread is not None:
            return
        thread = QThread()
        self._thread = thread
        self._worker.moveToThread(thread)
        thread.started.connect(self._worker.run)
        self._worker.test_finished.connect(thread.quit)
        thread.finished.connect(self._worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_finished)
        thread.start()

    def run(self):
        """兼容旧测试的同步执行入口；正常 UI 路径使用 start()。"""
        self._worker.run()

    def request_stop(self):
        self._worker.request_stop()

    def respond_confirm(self, continue_test):
        self._worker.respond_confirm(continue_test)

    def quit(self):
        """兼容主窗口统一清理契约，退出内部 QThread 事件循环。"""
        thread = self._thread
        if thread is not None:
            thread.quit()

    def wait(self, msecs=None):
        """等待内部 QThread 结束；尚未启动或已结束时立即成功。"""
        thread = self._thread
        if thread is None:
            return True
        if msecs is None:
            return thread.wait()
        return thread.wait(msecs)

    def _on_thread_finished(self):
        if self.sender() is self._thread:
            self._thread = None
