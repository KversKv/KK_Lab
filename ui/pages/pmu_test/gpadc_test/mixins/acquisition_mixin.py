"""GPADCTestUI UART / IIC 采样与数据整形 Mixin。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
类装配见 gpadc_test_ui.py。"""

import queue
import random
import time
from lib.i2c.i2c_interface_x64 import I2CInterface
from log_config import get_logger
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockChamber, MockI2C, MockN6705C
from instruments.chambers import TemperatureStabilizer
from core.pmu_test.gpadc import (
    compute_reg_stats, compute_calibration, parse_uart_gpadc_raw,
    parse_uart_gpadc_raw_volt, apply_algorithm, compare_algorithm_effect,
    filter_mean_deviation
)

logger = get_logger(__name__)


class _AcquisitionMixin:
    """UART / IIC 采样与数据整形 Mixin"""

    def _on_uart_rx_data(self, data):
        self._uart_rx_queue.put(bytes(data))

    def _drain_uart_rx_queue(self):
        while True:
            try:
                self._uart_rx_queue.get_nowait()
            except queue.Empty:
                break

    def _next_uart_log_line(self, partial, deadline, stop_check=None):
        while b"\n" not in partial:
            # 停止请求必须穿透内层等待：主线程一旦阻塞，串口数据泵（主线程槽）即断供，
            # 此循环会自旋到 deadline（默认 120s）且不查 stop_check，导致停止无响应、UI 卡死。
            if stop_check and stop_check():
                return partial, None
            remain = deadline - time.monotonic()
            if remain <= 0:
                return partial, None
            try:
                chunk = self._uart_rx_queue.get(timeout=min(0.1, remain))
            except queue.Empty:
                continue
            partial += chunk
        raw_line, partial = partial.split(b"\n", 1)
        return partial, raw_line.decode("utf-8", errors="replace").strip()

    def gpadc_uart_read_by_cnts(
        self,
        get_reg_cnt=1000,
        keyword="",
        timeout_s=120.0,
        return_raw=False,
        stop_check=None,
        progress_callback=None,
    ):
        if DEBUG_MOCK:
            rng = random.Random()
            raw_data = [max(0, int(rng.gauss(2844, 2.0))) for _ in range(get_reg_cnt)]
            if progress_callback:
                progress_callback(100)
            raw_data = self._apply_outlier_filter(raw_data)
            raw_data = self._apply_algo_tracked(raw_data)
            return compute_reg_stats(raw_data, return_raw=return_raw)

        raw_data = []
        partial = b""
        deadline = time.monotonic() + timeout_s
        while len(raw_data) < get_reg_cnt:
            if stop_check and stop_check():
                break
            if time.monotonic() >= deadline:
                self._test_worker.log.emit(
                    f"[WARN] UART 采集超时（{timeout_s:.0f}s），仅获取 {len(raw_data)}/{get_reg_cnt} 个样本，"
                    "请检查串口连接与 Search Keyword 是否匹配日志"
                )
                break
            partial, line = self._next_uart_log_line(partial, deadline, stop_check=stop_check)
            if line is None:
                continue
            value = parse_uart_gpadc_raw(line, keyword)
            if value is None:
                continue
            raw_data.append(value)
            if progress_callback:
                progress_callback(int(len(raw_data) * 100 / get_reg_cnt))

        if not raw_data:
            raise RuntimeError("未从 UART 日志提取到任何 GPADC 样本，请确认 DUT 日志输出与 Search Keyword 匹配")
        raw_data = self._apply_outlier_filter(raw_data)
        raw_data = self._apply_algo_tracked(raw_data)
        return compute_reg_stats(raw_data, return_raw=return_raw)

    def gpadc_uart_read_raw_volt_by_cnts(
        self,
        get_reg_cnt=1000,
        keyword="",
        timeout_s=120.0,
        stop_check=None,
        progress_callback=None,
    ):
        """从 UART 日志逐行解析 raw/volt 对（FT Calibration Check UART 方式用）。

        返回 (raw_avg, volt_avg)：raw 截尾均值（LSB）与 volt 截尾均值（mV，DUT
        已校准电压）。不应用采样算法——保持 raw 与 volt 的逐点配对一致性。
        """
        if DEBUG_MOCK:
            rng = random.Random()
            mock_v = self._mock_i2c._voltage if hasattr(self, "_mock_i2c") else 1.0
            raw_data = [max(0, int(mock_v * 3276.8 + rng.gauss(0, 2.0))) for _ in range(get_reg_cnt)]
            volt_data = [mock_v * 1000.0 + rng.gauss(0, 1.0) for _ in range(get_reg_cnt)]
            if progress_callback:
                progress_callback(100)
            raw_avg, _, _ = compute_reg_stats(raw_data)
            volt_avg, _, _ = compute_reg_stats(volt_data)
            return raw_avg, volt_avg

        pairs = []
        partial = b""
        deadline = time.monotonic() + timeout_s
        while len(pairs) < get_reg_cnt:
            if stop_check and stop_check():
                break
            if time.monotonic() >= deadline:
                self._test_worker.log.emit(
                    f"[WARN] UART 采集超时（{timeout_s:.0f}s），仅获取 {len(pairs)}/{get_reg_cnt} 个样本，"
                    "请检查串口连接与 Search Keyword 是否匹配日志"
                )
                break
            partial, line = self._next_uart_log_line(partial, deadline, stop_check=stop_check)
            if line is None:
                continue
            pair = parse_uart_gpadc_raw_volt(line, keyword)
            if pair is None:
                continue
            pairs.append(pair)
            if progress_callback:
                progress_callback(int(len(pairs) * 100 / get_reg_cnt))

        if not pairs:
            raise RuntimeError("未从 UART 日志提取到任何 GPADC raw/volt 样本，请确认 DUT 日志输出与 Search Keyword 匹配")
        raw_avg, _, _ = compute_reg_stats([p[0] for p in pairs])
        volt_avg, _, _ = compute_reg_stats([p[1] for p in pairs])
        return raw_avg, volt_avg

    def _gpadc_read_by_cnts(
        self,
        device_addr=0x17,
        reg_addr=0x56,
        iic_weight=10,
        get_reg_cnt=1000,
        return_raw=False,
        stop_check=None,
        progress_callback=None,
    ):
        if self._acq_mode_snapshot == 'UART':
            return self.gpadc_uart_read_by_cnts(
                get_reg_cnt=get_reg_cnt,
                keyword=self._uart_keyword_snapshot,
                return_raw=return_raw,
                stop_check=stop_check,
                progress_callback=progress_callback,
            )
        return self.gpadc_reg_read_by_cnts(
            device_addr=device_addr,
            reg_addr=reg_addr,
            iic_weight=iic_weight,
            get_reg_cnt=get_reg_cnt,
            return_raw=return_raw,
            stop_check=stop_check,
            progress_callback=progress_callback,
        )

    def _ensure_device_i2c(self):
        """获取（必要时创建）共享 I2C 接口，并按页面 IIC Speed 选择同步速度模式。

        速度在每次访问时重新赋值：设备掉线/接口重建后仍按当前快照生效，
        且多入口（GPADC 采样、多通道切换写、前置配置写）共用同一实例保持一致。
        """
        if not hasattr(self, "deviceI2C"):
            self.deviceI2C = I2CInterface()
            self.set_system_status("I2C接口初始化成功")
        self.deviceI2C.speed_mode = self._iic_speed_snapshot
        return self.deviceI2C

    def gpadc_reg_read_by_cnts(
        self,
        device_addr=0x17,
        reg_addr=0x56,
        iic_weight=10,
        get_reg_cnt=1000,
        return_raw=False,
        stop_check=None,
        progress_callback=None,
    ):
        if DEBUG_MOCK:
            if not hasattr(self, "_mock_i2c"):
                self._mock_i2c = MockI2C()
            deviceI2C = self._mock_i2c
        else:
            deviceI2C = self._ensure_device_i2c()

        raw_data = []

        for i in range(get_reg_cnt):
            if stop_check and stop_check():
                break
            temp = deviceI2C.read(device_addr, reg_addr, iic_weight)
            raw_data.append(temp)
            if progress_callback:
                progress_callback(int((i + 1) * 100 / get_reg_cnt))

        raw_data = self._apply_outlier_filter(raw_data)
        raw_data = self._apply_algo_tracked(raw_data)
        return compute_reg_stats(raw_data, return_raw=return_raw)

    def _check_sweep_response(self, voltage_data, adc_mean):
        """扫描响应保护：电压上升时前 N 点 Raw 均值应随之明显变化。

        返回 None 表示响应正常；返回字符串为告警原因（调用方据此中止测试）：
        - 极差 < 阈值：Raw 几乎不变（读数卡死 / 电压未施加 / 通道错误）
        - 净变化 <= 0：电压上升但 Raw 无净增量（方向异常 / DUT 无响应）
        """
        n = self._SWEEP_GUARD_POINTS
        if len(adc_mean) < n or len(voltage_data) < n:
            # 扫描点数不足（极小范围配置），不做判定
            return None
        head_v = voltage_data[:n]
        head_m = adc_mean[:n]
        spread = max(head_m) - min(head_m)
        net = head_m[-1] - head_m[0]
        detail = (
            f"前{n}点 V={[f'{v:.3f}' for v in head_v]}, "
            f"RawMean={[f'{m:.1f}' for m in head_m]}, "
            f"极差={spread:.1f} LSB, 净变化={net:+.1f} LSB"
        )
        if head_v[-1] > head_v[0] and net <= 0:
            return f"电压上升但 Raw 均值无净增量（疑似通道/地址/接线错误）。{detail}"
        if spread < self._SWEEP_GUARD_MIN_SPREAD_LSB:
            return f"Raw 均值几乎不随电压变化（疑似 DUT 无响应或电压未施加）。{detail}"
        return None

    def gpadc_force_voltage_test(
        self,
        n6705c=None,
        device_addr=0x17,
        reg_addr=0x56,
        iic_weight=10,
        voltage_min=0.1,
        voltage_max=1.8,
        voltage_step=0.05,
        voltage_channel=1,
        sample_cnt=1000,
        stop_check=None,
        progress_callback=None,
    ):
        self._test_worker.log.emit(f"[INFO] Running FORCE VOLTAGE TEST with I2C address: 0x{device_addr:x}, Register: 0x{reg_addr:x}")

        if DEBUG_MOCK:
            if not hasattr(self, "_mock_i2c"):
                self._mock_i2c = MockI2C()
            vol_source = MockN6705C()
            vol_source._mock_i2c = self._mock_i2c
        else:
            vol_source = n6705c if n6705c is not None else self.n6705c
            if vol_source is None or not self.is_connected:
                self._test_worker.log.emit("[ERROR] N6705C not connected")
                self.set_system_status("错误: N6705C未连接", is_error=True)
                return None

        settle_time = 0.0 if DEBUG_MOCK else 0.5
        step_time   = 0.0 if DEBUG_MOCK else 0.2

        voltage_data = []
        adc_mean = []
        adc_min = []
        adc_max = []
        # 逐点样本（曲线悬浮预览用）：raw_samples=处理后，raw_before_samples=算法前（未启用算法为 None 占位）
        raw_samples = []
        raw_before_samples = []

        vol_source.set_voltage(voltage_channel, voltage_min)
        time.sleep(settle_time)

        current_voltage = voltage_min
        total_points = max(1, int(round((voltage_max - voltage_min) / voltage_step)) + 1)
        point_idx = 0

        while current_voltage <= voltage_max + voltage_step * 0.001:
            if stop_check and stop_check():
                self._test_worker.log.emit("[INFO] Force voltage test stopped by user.")
                break
            vol_source.set_voltage(voltage_channel, current_voltage)
            time.sleep(step_time)

            avg, max_val, min_val, point_raw = self._gpadc_read_by_cnts(
                device_addr,
                reg_addr,
                iic_weight,
                get_reg_cnt=sample_cnt,
                return_raw=True,
                stop_check=stop_check,
            )
            # _apply_algo_tracked 刚更新过该点的算法前原始样本（未启用算法为 None）
            point_before = self._last_raw_before_algo

            voltage_data.append(current_voltage)
            adc_mean.append(avg)
            adc_min.append(min_val)
            adc_max.append(max_val)
            raw_samples.append(list(point_raw))
            raw_before_samples.append(list(point_before) if point_before is not None else None)

            # 响应保护：前 N 点 Raw 均值接近或方向异常 → 判定 DUT 无响应，中止测试
            if len(adc_mean) == self._SWEEP_GUARD_POINTS:
                guard_reason = self._check_sweep_response(voltage_data, adc_mean)
                if guard_reason is not None:
                    self._test_worker.log.emit(f"[WARN] GPADC response guard: {guard_reason}")
                    self._test_worker.log.emit("[WARN] Force voltage test 已中止，请检查 DUT 供电/接线/通道与采集配置")
                    self.set_system_status("警告: GPADC 无响应，测试已提前中止")
                    return None

            current_voltage = round(current_voltage + voltage_step, 6)
            point_idx += 1
            if progress_callback:
                progress_callback(int(point_idx * 100 / total_points))

        self._test_worker.log.emit("===== FORCE VOLTAGE TEST 结果 =====")

        result = {
            "voltage": voltage_data,
            "mean": adc_mean,
            "min": adc_min,
            "max": adc_max,
            "raw_samples": raw_samples,
            "raw_before_samples": raw_before_samples,
        }
        return result

    def _emit_worker_data_lines(self, header, data):
        """worker 线程安全的数据序列日志：header 行 + 值按 20 个/行分块（经 worker.log 信号）。"""
        self._test_worker.log.emit(header)
        for i in range(0, len(data), 20):
            self._test_worker.log.emit(
                ",".join(self._fmt_data_value(v) for v in data[i:i + 20])
            )

    def _apply_outlier_filter(self, raw_data):
        """按均值正/负向最大偏移筛除离群样本（worker 线程内调用）。

        未启用时原样返回；启用时在采样算法之前应用（先剔离群点再聚合），
        剔除数量与被剔除样本值写日志；阈值过严导致全剔除时回退原始数据并告警。
        """
        cfg = self._outlier_filter_snapshot
        if not cfg or not raw_data:
            return raw_data
        kept, removed = filter_mean_deviation(raw_data, cfg['pos'], cfg['neg'])
        if not removed:
            return raw_data
        mean_val = sum(raw_data) / len(raw_data)
        if not kept:
            self._emit_worker_data_lines(
                f"[WARN] 离群筛选阈值（均值 {self._fmt_data_value(mean_val)}，"
                f"+{cfg['pos']:.1f}/-{cfg['neg']:.1f} LSB）过严，"
                f"全部 {len(raw_data)} 个样本均被剔除，已回退为原始数据；被剔除值 (N={len(removed)}):",
                removed,
            )
            return raw_data
        self._emit_worker_data_lines(
            f"[FILTER] 剔除 {len(removed)}/{len(raw_data)} 个离群样本"
            f"（均值 {self._fmt_data_value(mean_val)}，+{cfg['pos']:.1f}/-{cfg['neg']:.1f} LSB），"
            f"被剔除值 (N={len(removed)}):",
            removed,
        )
        return kept

    def _apply_algo_tracked(self, raw_data):
        """应用采样算法并记录前后统计对比到 _last_algo_effect（worker 线程内调用）。

        未启用算法时原样返回并清空对比记录；对比结果供 1000CNT 完成日志
        输出算法带来的波动改善。
        """
        if not self._algorithm_snapshot:
            self._last_algo_effect = None
            self._last_raw_before_algo = None
            return raw_data
        before = list(raw_data)
        processed = apply_algorithm(raw_data, self._algorithm_snapshot)
        self._last_algo_effect = compare_algorithm_effect(before, processed)
        self._last_raw_before_algo = before
        return processed

    def _calibration_data(self, result):
        adc_raw_data = result["voltage"]
        adc_mean     = result["mean"]
        adc_min      = result["min"]
        adc_max      = result["max"]

        k, b, mean_cali, adc_min_cali, adc_max_cali, v_low, m_low, v_high, m_high = \
            compute_calibration(adc_raw_data, adc_mean, adc_min, adc_max,
                                calib_points=self._calib_points_snapshot)

        if k == 0.0:
            self._append_log(
                "[WARN] 标定斜率 k=0（ADC 读数无变化或采样点电压相同），跳过标定，使用原始数据"
            )
        self._append_log(f"[INFO] Calibration: k={k:.6f} (LSB/V), b={b:.6f} (LSB)")

        self._append_log(
            'Voltage,RawMean,mean_cali,Δmean(mV),RawMin,RawMax,min_cali,max_cali,Δmin(mV),Δmax(mV)'
        )
        n = len(adc_raw_data)
        for i in range(n):
            v_in = adc_raw_data[i]
            delta_mean_mv = (mean_cali[i] - v_in) * 1000
            delta_min_mv = (adc_min_cali[i] - v_in) * 1000
            delta_max_mv = (adc_max_cali[i] - v_in) * 1000
            self._append_log(
                f'{v_in:.4f},{adc_mean[i]:.3f},{mean_cali[i]:.6f},{delta_mean_mv:+.3f}'
                f',{adc_min[i]},{adc_max[i]}'
                f',{adc_min_cali[i]:.6f},{adc_max_cali[i]:.6f}'
                f',{delta_min_mv:+.3f},{delta_max_mv:+.3f}'
            )

        self._append_log(f"[INFO] calibration points: v_low={v_low:.4f}, m_low={m_low:.3f}, v_high={v_high:.4f}, m_high={m_high:.3f}")
        self._append_log(f"[INFO] Calibration: k={k:.6f} (LSB/V), b={b:.6f} (LSB)")

        return adc_raw_data, mean_cali, adc_min_cali, adc_max_cali

    def _compute_multi_ch_calibration(self, result):
        """多通道温度测试：扫压通道逐温度行两点标定（与 temp_consistency 同语义）。

        标定矩阵附回 channel dict（mean_cali/min_cali/max_cali），供绘图与导出使用。
        定点采样通道无输入参考扫描，不做标定。
        """
        for ch in (result.get('channels') or []):
            if not ch.get('sweep'):
                continue
            vpts = ch.get('voltage') or []
            mean_rows = ch.get('mean') or []
            min_rows = ch.get('min') or []
            max_rows = ch.get('max') or []
            mean_cali_rows, min_cali_rows, max_cali_rows = [], [], []
            k = b = 0.0
            for i in range(len(mean_rows)):
                k, b, mean_cali, min_cali, max_cali, *_ = compute_calibration(
                    vpts, mean_rows[i],
                    min_rows[i] if i < len(min_rows) else [],
                    max_rows[i] if i < len(max_rows) else [],
                    calib_points=self._calib_points_snapshot,
                )
                mean_cali_rows.append(mean_cali)
                min_cali_rows.append(min_cali)
                max_cali_rows.append(max_cali)
            ch['mean_cali'] = mean_cali_rows
            ch['min_cali'] = min_cali_rows
            ch['max_cali'] = max_cali_rows
            if mean_cali_rows:
                self._append_log(
                    f"[INFO] CH {ch.get('name')}: Calibration k={k:.6f} (LSB/V), b={b:.6f} (LSB)"
                )

    def gpadc_high_low_temp_test(
        self,
        device_addr=0x17,
        reg_addr=0x56,
        iic_weight=10,
        temp_min=0,
        temp_max=100,
        temp_step=1,
        voltage_channel=100,
        soak_time=180,
        sample_cnt=1000,
        stop_check=None,
        progress_callback=None,
    ):
        try:
            if DEBUG_MOCK:
                if not hasattr(self, "_mock_i2c"):
                    self._mock_i2c = MockI2C()
                chamber = MockChamber()
                deviceI2C = self._mock_i2c
            else:
                if not hasattr(self, 'chamber') or not self.is_chamber_connected:
                    self._test_worker.log.emit("[ERROR] Chamber not connected")
                    self.set_system_status("错误: 温箱未连接", is_error=True)
                    return None
                if self._acq_mode_snapshot == 'UART':
                    deviceI2C = None
                else:
                    deviceI2C = self._ensure_device_i2c()
                chamber = self.chamber

            if deviceI2C is not None:
                test_data = deviceI2C.read(device_addr, reg_addr, iic_weight)
                self._test_worker.log.emit(f"[INFO] Test data: {test_data:x}")

            temp_data = []
            adc_mean = []
            adc_min = []
            adc_max = []
            adc_raw_all = []

            current_temp = temp_min
            total_points = max(1, int(round((temp_max - temp_min) / temp_step)) + 1)
            point_idx = 0

            while current_temp <= temp_max + 0.001:
                if stop_check and stop_check():
                    self._test_worker.log.emit("[INFO] High/Low temp test stopped by user.")
                    break

                try:
                    chamber.set_temperature(current_temp)
                    self.set_system_status(f"设置温箱温度到 {current_temp:.1f}°C")

                    if DEBUG_MOCK:
                        self._test_worker.log.emit(f"[DEBUG] Temp set to {current_temp:.1f}°C (instant)")
                    else:
                        if point_idx == 0:
                            try:
                                chamber.start()
                                self._test_worker.log.emit("[INFO] Chamber started (constant-temp run command sent)")
                            except Exception as e:
                                self._test_worker.log.emit(f"[WARN] Chamber start command failed: {e}")

                        stabilizer = TemperatureStabilizer(
                            chamber,
                            log_fn=self._test_worker.log.emit,
                            stop_check=stop_check,
                            max_read_failures=12,
                        )
                        result = stabilizer.wait_for_stable(current_temp)

                        if result.reason == "stopped":
                            self._test_worker.log.emit("[INFO] High/Low temp test stopped by user.")
                            break

                        actual_str = "N/A" if result.actual is None else f"{result.actual:.2f}"
                        self._test_worker.log.emit(
                            f"[INFO] Temperature {result.reason}: target={current_temp:.1f}, "
                            f"actual={actual_str}, waited {result.waited_s:.0f}s, polls={result.poll_count}"
                        )

                        self.set_system_status(f"DUT温度均衡中: {current_temp:.1f}°C")
                        for _ in range(int(soak_time)):
                            if stop_check and stop_check():
                                break
                            time.sleep(1)

                        if stop_check and stop_check():
                            self._test_worker.log.emit("[INFO] High/Low temp test stopped by user.")
                            break

                    if DEBUG_MOCK:
                        self._mock_i2c.set_mock_voltage(current_temp / 100.0)

                    avg, max_val, min_val, raw_data = self._gpadc_read_by_cnts(
                        device_addr,
                        reg_addr,
                        iic_weight,
                        get_reg_cnt=sample_cnt,
                        return_raw=True,
                        stop_check=stop_check,
                    )
                except Exception as e:
                    # 可恢复错误（典型：温箱 USB 串口瞬时中断 WriteFile AccessDenied）
                    # → 弹窗让用户恢复环境后重试当前温度点，避免长周期测试整体报废
                    logger.warning("高低温测试温度点 %.1f°C 执行失败: %s", current_temp, e, exc_info=True)
                    retry = False
                    stopped = False
                    if not DEBUG_MOCK:
                        answered, retry = self._test_worker.wait_user_confirm(
                            "温箱通信失败",
                            f"温度点 {current_temp:.1f}°C 执行失败：\n{e}\n\n"
                            "常见原因：USB 串口转换器瞬时掉线、端口被其它程序占用、USB 电源管理挂起。\n"
                            "请检查温箱串口连接并恢复环境后：\n"
                            "· 【重试】重新打开串口，重测当前温度点（已测数据保留）\n"
                            "· 【中止】结束测试，输出已测温度点数据",
                        )
                        stopped = not answered
                    if stopped:
                        self._test_worker.log.emit("[INFO] High/Low temp test stopped by user.")
                    elif not retry:
                        self._test_worker.log.emit(
                            f"[WARN] 温度点 {current_temp:.1f}°C 执行失败且未重试，测试提前结束（已测数据保留）"
                        )
                    if not retry:
                        break
                    try:
                        chamber.disconnect()
                        chamber.connect()
                        self._test_worker.log.emit("[INFO] 温箱串口已重新打开，重试当前温度点")
                    except Exception as e2:
                        self._test_worker.log.emit(f"[WARN] 温箱串口重开失败: {e2}")
                    continue

                temp_data.append(current_temp)
                adc_mean.append(avg)
                adc_min.append(min_val)
                adc_max.append(max_val)
                adc_raw_all.append(raw_data)

                self._test_worker.log.emit(f"[INFO] T={current_temp:.1f}°C, avg={avg:.3f}, min={min_val}, max={max_val}")

                current_temp += temp_step
                point_idx += 1
                if progress_callback:
                    progress_callback(int(point_idx * 100 / total_points))
                time.sleep(1)
            try:
                chamber.set_temperature(25.0)
            except Exception as e:
                # 中止场景串口可能仍断开，恢复常温失败不应冲掉已测数据
                self._test_worker.log.emit(f"[WARN] 恢复温箱 25°C 失败: {e}，请手动检查温箱状态")
            self._test_worker.log.emit("===== HIGH/LOW TEMP TEST 结果 =====")
            self._test_worker.log.emit("Temp, RawMean, RawMin, RawMax")
            for i in range(len(temp_data)):
                self._test_worker.log.emit(f"{temp_data[i]:.2f}, {adc_mean[i]:.3f}, {adc_min[i]}, {adc_max[i]}")

            return {
                "voltage": temp_data,
                "mean": adc_mean,
                "min": adc_min,
                "max": adc_max,
            }

        except Exception as e:
            self._test_worker.log.emit(f"[ERROR] {e}")
            logger.error("测试执行错误: %s", e, exc_info=True)
            self.set_system_status(f"错误: {e}", is_error=True)
            return None

    def gpadc_temp_consistency_test(
        self,
        device_addr=0x17,
        reg_addr=0x56,
        iic_weight=10,
        temp_min=0,
        temp_max=100,
        temp_step=1,
        voltage_min=0.1,
        voltage_max=1.8,
        voltage_step=0.05,
        voltage_channel=1,
        soak_time=180,
        sample_cnt=1000,
        stop_check=None,
        progress_callback=None,
    ):
        self._test_worker.log.emit(f"[INFO] Running TEMP CONSISTENCY TEST with I2C address: 0x{device_addr:x}, Register: 0x{reg_addr:x}")

        if DEBUG_MOCK:
            if not hasattr(self, "_mock_i2c"):
                self._mock_i2c = MockI2C()
                chamber = MockChamber()
            vol_source = MockN6705C()
            vol_source._mock_i2c = self._mock_i2c
        else:
            if not hasattr(self, 'chamber') or not self.is_chamber_connected:
                self._test_worker.log.emit("[ERROR] Chamber not connected")
                self.set_system_status("错误: 温箱未连接", is_error=True)
                return None
            if self.n6705c is None or not self.is_connected:
                self._test_worker.log.emit("[ERROR] N6705C not connected")
                self.set_system_status("错误: N6705C未连接", is_error=True)
                return None
            if self._acq_mode_snapshot != 'UART':
                self._ensure_device_i2c()
            chamber = self.chamber
            vol_source = self.n6705c

        settle_time = 0.0 if DEBUG_MOCK else 0.5
        step_time   = 0.0 if DEBUG_MOCK else 0.2

        voltage_points = []
        v = voltage_min
        while v <= voltage_max + voltage_step * 0.001:
            voltage_points.append(round(v, 6))
            v = round(v + voltage_step, 6)

        temp_list   = []
        mean_matrix = []
        min_matrix  = []
        max_matrix  = []

        total_temp_points = max(1, int(round((temp_max - temp_min) / temp_step)) + 1)
        total_voltage_points = len(voltage_points)
        total_steps = total_temp_points * total_voltage_points
        completed_steps = 0

        current_temp = temp_min
        while current_temp <= temp_max + 0.001:
            if stop_check and stop_check():
                self._test_worker.log.emit("[INFO] Temp consistency test stopped by user.")
                break

            chamber.set_temperature(current_temp)
            self.set_system_status(f"设置温箱温度到 {current_temp:.1f}°C")

            if DEBUG_MOCK:
                self._test_worker.log.emit(f"[DEBUG] Temp set to {current_temp:.1f}°C (instant)")
            else:
                history = []
                stable_count = 0
                while True:
                    if stop_check and stop_check():
                        break
                    actual_temp = chamber.get_current_temp()
                    history.append(actual_temp)
                    if len(history) > 10:
                        history.pop(0)
                    if len(history) >= 5:
                        if max(history) - min(history) < 0.2:
                            stable_count += 1
                        else:
                            stable_count = 0
                        if stable_count >= 3:
                            break
                    self._test_worker.log.emit(f"[INFO] Temp stabilizing: target={current_temp:.1f}, actual={actual_temp:.2f}")
                    # 30s 轮询间隔切成 1s 片，保证停止请求可及时打断（日志节奏不变）
                    for _ in range(30):
                        if stop_check and stop_check():
                            break
                        time.sleep(1)

                if stop_check and stop_check():
                    self._test_worker.log.emit("[INFO] Temp consistency test stopped by user.")
                    break

                self.set_system_status(f"DUT温度均衡中: {current_temp:.1f}°C")
                for _ in range(int(soak_time)):
                    if stop_check and stop_check():
                        break
                    time.sleep(1)

                if stop_check and stop_check():
                    self._test_worker.log.emit("[INFO] Temp consistency test stopped by user.")
                    break

            mean_row = []
            min_row  = []
            max_row  = []

            vol_source.set_voltage(voltage_channel, voltage_min)
            time.sleep(settle_time)

            for vpt in voltage_points:
                if stop_check and stop_check():
                    break
                vol_source.set_voltage(voltage_channel, vpt)
                time.sleep(step_time)

                avg, max_val, min_val = self._gpadc_read_by_cnts(
                    device_addr,
                    reg_addr,
                    iic_weight,
                    get_reg_cnt=sample_cnt,
                    return_raw=False,
                    stop_check=stop_check,
                )
                mean_row.append(avg)
                min_row.append(min_val)
                max_row.append(max_val)
                completed_steps += 1
                if progress_callback:
                    progress_callback(int(completed_steps * 100 / total_steps))

            if stop_check and stop_check():
                break

            temp_list.append(current_temp)
            mean_matrix.append(mean_row)
            min_matrix.append(min_row)
            max_matrix.append(max_row)

            self._test_worker.log.emit(f"[INFO] T={current_temp:.1f}°C  voltage sweep done ({len(mean_row)} points)")
            current_temp = round(current_temp + temp_step, 6)

        vol_header = "  ".join(f"{v:.3f}" for v in voltage_points)

        self._test_worker.log.emit("===== TEMP CONSISTENCY TEST 结果 (Mean) =====")
        self._test_worker.log.emit("Temp\\Voltage  " + vol_header)
        for i, t in enumerate(temp_list):
            if i < len(mean_matrix):
                row = "  ".join(f"{mean_matrix[i][j]:.1f}" for j in range(len(mean_matrix[i])))
                self._test_worker.log.emit(f"T={t:.1f}  {row}")

        self._test_worker.log.emit("===== TEMP CONSISTENCY TEST 结果 (Min) =====")
        self._test_worker.log.emit("Temp\\Voltage  " + vol_header)
        for i, t in enumerate(temp_list):
            if i < len(min_matrix):
                row = "  ".join(f"{min_matrix[i][j]:.1f}" for j in range(len(min_matrix[i])))
                self._test_worker.log.emit(f"T={t:.1f}  {row}")

        self._test_worker.log.emit("===== TEMP CONSISTENCY TEST 结果 (Max) =====")
        self._test_worker.log.emit("Temp\\Voltage  " + vol_header)
        for i, t in enumerate(temp_list):
            if i < len(max_matrix):
                row = "  ".join(f"{max_matrix[i][j]:.1f}" for j in range(len(max_matrix[i])))
                self._test_worker.log.emit(f"T={t:.1f}  {row}")

        mean_cali_matrix = []
        min_cali_matrix = []
        max_cali_matrix = []
        for i, t in enumerate(temp_list):
            if i < len(mean_matrix):
                row_result = {
                    "voltage": voltage_points,
                    "mean": mean_matrix[i],
                    "min": min_matrix[i],
                    "max": max_matrix[i],
                }
                _, mean_cali, min_cali, max_cali = self._calibration_data(row_result)
                mean_cali_matrix.append(mean_cali)
                min_cali_matrix.append(min_cali)
                max_cali_matrix.append(max_cali)

        self._test_worker.log.emit("===== TEMP CONSISTENCY TEST 校准结果 (Mean Cali) =====")
        self._test_worker.log.emit("Temp\\Voltage  " + vol_header)
        for i, t in enumerate(temp_list):
            if i < len(mean_cali_matrix):
                row = "  ".join(f"{mean_cali_matrix[i][j]:.6f}" for j in range(len(mean_cali_matrix[i])))
                self._test_worker.log.emit(f"T={t:.1f}  {row}")

        self._test_worker.log.emit("===== TEMP CONSISTENCY TEST 校准结果 (Min Cali) =====")
        self._test_worker.log.emit("Temp\\Voltage  " + vol_header)
        for i, t in enumerate(temp_list):
            if i < len(min_cali_matrix):
                row = "  ".join(f"{min_cali_matrix[i][j]:.6f}" for j in range(len(min_cali_matrix[i])))
                self._test_worker.log.emit(f"T={t:.1f}  {row}")

        self._test_worker.log.emit("===== TEMP CONSISTENCY TEST 校准结果 (Max Cali) =====")
        self._test_worker.log.emit("Temp\\Voltage  " + vol_header)
        for i, t in enumerate(temp_list):
            if i < len(max_cali_matrix):
                row = "  ".join(f"{max_cali_matrix[i][j]:.6f}" for j in range(len(max_cali_matrix[i])))
                self._test_worker.log.emit(f"T={t:.1f}  {row}")

        return {
            "temp":    temp_list,
            "voltage": voltage_points,
            "mean":    mean_matrix,
            "min":     min_matrix,
            "max":     max_matrix,
            "mean_cali": mean_cali_matrix,
            "min_cali":  min_cali_matrix,
            "max_cali":  max_cali_matrix,
        }

    def _calculate_gpadc_parameters(self, force_voltage_result):
        """
        基于 gpadc_force_voltage_test 的返回值计算 GPADC 性能参数。

        force_voltage_result 格式:
            {
                "voltage": [v0, v1, ...],   # 输入电压 (V)
                "mean":    [m0, m1, ...],   # 每个电压点的 ADC 均值
                "min":     [n0, n1, ...],   # 每个电压点的 ADC 最小值
                "max":     [x0, x1, ...],   # 每个电压点的 ADC 最大值
            }

        返回 params dict，包含:
            linearity, dnl, inl, enob, gain_error, offset_error,
            avg, min, max
        """
        import numpy as np

        voltage = np.array(force_voltage_result["voltage"], dtype=float)
        adc_mean = np.array(force_voltage_result["mean"], dtype=float)
        adc_min = np.array(force_voltage_result["min"], dtype=float)
        adc_max = np.array(force_voltage_result["max"], dtype=float)

        n = len(voltage)
        params = {}

        params['avg'] = float(np.mean(adc_mean))
        params['max'] = float(np.max(adc_max))
        params['min'] = float(np.min(adc_min))

        if n < 2:
            params.update({'linearity': 0.0, 'dnl': 0.0, 'inl': 0.0,
                           'enob': 0.0, 'gain_error': 0.0, 'offset_error': 0.0})
            return params

        # ── 线性拟合 voltage → adc_mean ──────────────────────────────
        coeffs = np.polyfit(voltage, adc_mean, 1)
        slope = coeffs[0]       # LSB/V
        intercept = coeffs[1]
        adc_ideal = np.polyval(coeffs, voltage)

        # Linearity: R²（越接近1越好）
        ss_res = np.sum((adc_mean - adc_ideal) ** 2)
        ss_tot = np.sum((adc_mean - np.mean(adc_mean)) ** 2)
        params['linearity'] = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 1.0

        # ── INL (Integral Non-Linearity) ──────────────────────────────
        # 每个采样点与理想线性值的偏差，取峰峰值的一半（LSB）
        inl_values = adc_mean - adc_ideal
        params['inl'] = float(np.max(np.abs(inl_values)))

        # ── DNL (Differential Non-Linearity) ─────────────────────────
        # 相邻步进的实际ADC增量 vs 理想增量之差（LSB）
        ideal_step = slope * (voltage[1] - voltage[0])   # 理想单步增量（LSB）
        actual_steps = np.diff(adc_mean)
        if ideal_step != 0:
            dnl_values = (actual_steps - ideal_step) / abs(ideal_step)
            params['dnl'] = float(np.max(np.abs(dnl_values)))
        else:
            params['dnl'] = 0.0

        # ── ENOB (Effective Number of Bits) ──────────────────────────
        # 用每个采样点的噪声范围（max-min）估算 RMS 噪声，再计算 SINAD→ENOB
        noise_pp = adc_max - adc_min          # peak-to-peak 噪声
        noise_rms = np.mean(noise_pp) / (2 * np.sqrt(3))   # 均匀分布近似
        adc_full_range = params['max'] - params['min']
        if noise_rms > 0 and adc_full_range > 0:
            snr_db = 20 * np.log10(adc_full_range / (noise_rms * 2 * np.sqrt(3)))
            params['enob'] = float(max(0.0, (snr_db - 1.76) / 6.02))
        else:
            params['enob'] = 0.0

        # ── Gain Error ────────────────────────────────────────────────
        # 理想斜率 = (ADC满量程范围) / (电压满量程范围)
        volt_range = float(voltage[-1] - voltage[0])
        adc_range = float(adc_mean[-1] - adc_mean[0])
        if volt_range > 0:
            ideal_slope = adc_range / volt_range
            params['gain_error'] = float(((slope - ideal_slope) / ideal_slope) * 100) if ideal_slope != 0 else 0.0
        else:
            params['gain_error'] = 0.0

        # ── Offset Error ──────────────────────────────────────────────
        # 拟合线在最小电压处的预测值与实际测量值的偏差（LSB）
        params['offset_error'] = float(adc_ideal[0] - adc_mean[0])
        self._append_log(f"[RESULT] INL={params['inl']:.3f}, DNL={params['dnl']:.3f}, ENOB={params['enob']:.3f}, Gain Error: {params['gain_error']:.3f}%, Offset Error: {params['offset_error']:.3f} LSB")
        return params
