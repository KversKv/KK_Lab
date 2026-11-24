# -*- coding: utf-8 -*-
"""GPADC 采样与七类测试编排（纯 Python，无 UI / Qt 依赖）。

仪器、UART 队列、IIC、采样配置和通知回调均由调用方显式注入；
返回协议保持为 ``(kind, result)``，供 ``gpadc_worker.TestWorker`` 直接调用。
"""

from contextlib import contextmanager
import math
import queue
import random
import time

from instruments.chambers import TemperatureStabilizer
from log_config import get_logger

from .gpadc_analysis import (
    advance_linearity_auto_best,
    aggregate_linearity_repeats,
    algorithm_length_divisor,
    analyze_linearity_group,
    apply_algorithm,
    compare_algorithm_effect,
    compute_calibration,
    compute_detailed_stats,
    compute_reg_stats,
    filter_mean_deviation,
    format_log_table,
    generate_linearity_pairs,
    normalize_linearity_auto_range,
    parse_uart_gpadc_raw,
    parse_uart_gpadc_raw_volt,
    select_best_linearity_group,
)
from .gpadc_ft_check import run_ft_calib_check
from .gpadc_multi_temp import parse_hw_int, run_multi_ch_temp_test

logger = get_logger(__name__)


def _fmt_data_value(value):
    return str(int(value)) if float(value).is_integer() else f"{float(value):.2f}"


class GPADCAcquisition:
    """UART / IIC 纯采样器；UART 数据只从注入队列消费，不接触 Widget。"""

    def __init__(
        self,
        *,
        mode,
        keyword="",
        uart_queue=None,
        i2c=None,
        i2c_factory=None,
        iic_speed=None,
        mock_i2c=None,
        mock_mode=False,
        algorithm=None,
        outlier_filter=None,
        log_fn=None,
        status_fn=None,
    ):
        self.mode = str(mode).upper()
        self.keyword = keyword
        self.uart_queue = uart_queue
        self.i2c = i2c
        self.i2c_factory = i2c_factory
        self.iic_speed = iic_speed
        self.mock_i2c = mock_i2c
        self.mock_mode = bool(mock_mode)
        self.algorithm = algorithm
        self.outlier_filter = outlier_filter
        self.log_fn = log_fn or (lambda message: None)
        self.status_fn = status_fn or (lambda message, is_error=False: None)
        self.last_algo_effect = None
        self.last_raw_before_algo = None

    @contextmanager
    def processing_disabled(self):
        """FT 检查期间保持 raw/volt 配对，结束后恢复采样处理配置。"""
        saved_algorithm = self.algorithm
        saved_filter = self.outlier_filter
        self.algorithm = None
        self.outlier_filter = None
        try:
            yield
        finally:
            self.algorithm = saved_algorithm
            self.outlier_filter = saved_filter

    def ensure_i2c(self):
        if self.mock_mode:
            if self.mock_i2c is None:
                raise RuntimeError("Mock GPADC 采样缺少 mock_i2c")
            return self.mock_i2c
        if self.i2c is None:
            if self.i2c_factory is None:
                raise RuntimeError("IIC 采样缺少 i2c 或 i2c_factory")
            self.i2c = self.i2c_factory()
            self.status_fn("I2C接口初始化成功", False)
        self.i2c.speed_mode = self.iic_speed
        return self.i2c

    def write_reg(self, dev, reg, val, width, high=-1, low=-1):
        device = self.ensure_i2c()
        if self.mock_mode:
            device.write(dev, reg, val, width)
            return
        device.write(dev, reg, val, width, high, low)

    def read_reg(self, dev, reg, width):
        return self.ensure_i2c().read(dev, reg, width)

    def _next_uart_log_line(self, partial, deadline, stop_check=None):
        if self.uart_queue is None:
            raise RuntimeError("UART 采样缺少 uart_queue")
        while b"\n" not in partial:
            if stop_check and stop_check():
                return partial, None
            remain = deadline - time.monotonic()
            if remain <= 0:
                return partial, None
            try:
                chunk = self.uart_queue.get(timeout=min(0.1, remain))
            except queue.Empty:
                continue
            partial += chunk
        raw_line, partial = partial.split(b"\n", 1)
        return partial, raw_line.decode("utf-8", errors="replace").strip()

    def _emit_data_lines(self, header, data):
        self.log_fn(header)
        if not data:
            return
        texts = [_fmt_data_value(value) for value in data]
        width = max(len(text) for text in texts)
        for index in range(0, len(texts), 20):
            self.log_fn("[DATA] " + ",".join(
                text.rjust(width) for text in texts[index:index + 20]))

    def apply_outlier_filter(self, raw_data):
        cfg = self.outlier_filter
        if not cfg or not raw_data:
            return raw_data
        kept, removed = filter_mean_deviation(raw_data, cfg["pos"], cfg["neg"])
        if not removed:
            return raw_data
        mean_val = sum(raw_data) / len(raw_data)
        if not kept:
            self._emit_data_lines(
                f"[WARN] 离群筛选阈值（均值 {_fmt_data_value(mean_val)}，"
                f"+{cfg['pos']:.1f}/-{cfg['neg']:.1f} LSB）过严，"
                f"全部 {len(raw_data)} 个样本均被剔除，已回退为原始数据；被剔除值 (N={len(removed)}):",
                removed,
            )
            return raw_data
        self._emit_data_lines(
            f"[FILTER] 剔除 {len(removed)}/{len(raw_data)} 个离群样本"
            f"（均值 {_fmt_data_value(mean_val)}，+{cfg['pos']:.1f}/-{cfg['neg']:.1f} LSB），"
            f"被剔除值 (N={len(removed)}):",
            removed,
        )
        return kept

    def apply_algorithm_tracked(self, raw_data):
        if not self.algorithm:
            self.last_algo_effect = None
            self.last_raw_before_algo = None
            return raw_data
        before = list(raw_data)
        processed = apply_algorithm(raw_data, self.algorithm)
        self.last_algo_effect = compare_algorithm_effect(before, processed)
        self.last_raw_before_algo = before
        return processed

    def _process(self, raw_data):
        raw_data = self.apply_outlier_filter(raw_data)
        return self.apply_algorithm_tracked(raw_data)

    def uart_read_by_cnts(
        self,
        get_reg_cnt=1000,
        keyword="",
        timeout_s=120.0,
        return_raw=False,
        stop_check=None,
        progress_callback=None,
    ):
        if self.mock_mode:
            rng = random.Random()
            raw_data = [max(0, int(rng.gauss(2844, 2.0))) for _ in range(get_reg_cnt)]
            if progress_callback:
                progress_callback(100)
            return compute_reg_stats(self._process(raw_data), return_raw=return_raw)

        raw_data = []
        partial = b""
        deadline = time.monotonic() + timeout_s
        while len(raw_data) < get_reg_cnt:
            if stop_check and stop_check():
                break
            if time.monotonic() >= deadline:
                self.log_fn(
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
        return compute_reg_stats(self._process(raw_data), return_raw=return_raw)

    def uart_read_raw_volt_by_cnts(
        self,
        get_reg_cnt=1000,
        keyword="",
        timeout_s=120.0,
        stop_check=None,
        progress_callback=None,
    ):
        if self.mock_mode:
            rng = random.Random()
            mock_v = self.mock_i2c._voltage if self.mock_i2c is not None else 1.0
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
                self.log_fn(
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
        raw_avg, _, _ = compute_reg_stats([pair[0] for pair in pairs])
        volt_avg, _, _ = compute_reg_stats([pair[1] for pair in pairs])
        return raw_avg, volt_avg

    def reg_read_by_cnts(
        self,
        device_addr=0x17,
        reg_addr=0x56,
        iic_weight=10,
        get_reg_cnt=1000,
        return_raw=False,
        stop_check=None,
        progress_callback=None,
    ):
        device = self.ensure_i2c()
        raw_data = []
        for index in range(get_reg_cnt):
            if stop_check and stop_check():
                break
            raw_data.append(device.read(device_addr, reg_addr, iic_weight))
            if progress_callback:
                progress_callback(int((index + 1) * 100 / get_reg_cnt))
        if not raw_data:
            raise RuntimeError("未从 IIC 读取到任何 GPADC 样本，采样可能已停止")
        return compute_reg_stats(self._process(raw_data), return_raw=return_raw)

    def read_by_cnts(
        self,
        device_addr=0x17,
        reg_addr=0x56,
        iic_weight=10,
        get_reg_cnt=1000,
        return_raw=False,
        stop_check=None,
        progress_callback=None,
    ):
        if self.mode == "UART":
            return self.uart_read_by_cnts(
                get_reg_cnt=get_reg_cnt,
                keyword=self.keyword,
                return_raw=return_raw,
                stop_check=stop_check,
                progress_callback=progress_callback,
            )
        return self.reg_read_by_cnts(
            device_addr=device_addr,
            reg_addr=reg_addr,
            iic_weight=iic_weight,
            get_reg_cnt=get_reg_cnt,
            return_raw=return_raw,
            stop_check=stop_check,
            progress_callback=progress_callback,
        )


class GPADCTestRunner:
    """六类 GPADC 测试的 worker 侧编排，全部副作用经显式依赖执行。"""

    def __init__(
        self,
        *,
        acquisition,
        n6705c=None,
        chamber=None,
        n6705c_connected=False,
        chamber_connected=False,
        mock_mode=False,
        calib_points=None,
        log_fn=None,
        status_fn=None,
        progress_callback=None,
        confirm_fn=None,
        sweep_guard_points=3,
        sweep_guard_min_spread_lsb=2,
    ):
        self.acquisition = acquisition
        self.n6705c = n6705c
        self.chamber = chamber
        self.n6705c_connected = bool(n6705c_connected)
        self.chamber_connected = bool(chamber_connected)
        self.mock_mode = bool(mock_mode)
        self.calib_points = calib_points
        self.log_fn = log_fn or (lambda message: None)
        self.status_fn = status_fn or (lambda message, is_error=False: None)
        self.progress_callback = progress_callback or (lambda value: None)
        self.confirm_fn = confirm_fn
        self.sweep_guard_points = int(sweep_guard_points)
        self.sweep_guard_min_spread_lsb = sweep_guard_min_spread_lsb

    def run(self, kind, config, stop_check=None):
        methods = {
            "1000cnt": self._run_1000cnt,
            "force_voltage": self._run_force_voltage,
            "linearity_traverse": self._run_linearity_traverse,
            "high_low_temp": self._run_high_low_temp,
            "temp_consistency": self._run_temp_consistency,
            "multi_ch_temp": self._run_multi_ch_temp,
            "ft_calib_check": self._run_ft_calib_check,
        }
        try:
            method = methods[kind]
        except KeyError as exc:
            raise ValueError(f"未知 GPADC 测试类型: {kind}") from exc

        channels = self._voltage_channels_for_test(kind, config)
        if not channels or self.mock_mode or self.n6705c is None:
            return method(config, stop_check)

        saved = {}
        for channel in channels:
            try:
                saved[channel] = {
                    "voltage": self.n6705c.measure_voltage(channel),
                    "mode": self.n6705c.get_mode(channel),
                    "enabled": bool(self.n6705c.get_channel_state(channel)),
                }
            except Exception as exc:
                self.log_fn(f"[ERROR] 读取 CH{channel} 测试前状态失败: {exc}")
                logger.error("GPADC 读取 CH%s 测试前状态失败", channel, exc_info=True)
                raise
        try:
            for channel in channels:
                self.n6705c.set_mode(channel, "PS2Q")
                self.n6705c.channel_on(channel)
                self.log_fn(f"[INFO] CH{channel} 已设置为 PS2Q 并开启输出")
            return method(config, stop_check)
        finally:
            for channel, state in saved.items():
                try:
                    self.n6705c.set_voltage(channel, state["voltage"])
                    self.log_fn(f"[INFO] CH{channel} 电压已恢复测试前设定: {state['voltage']:.2f} V")
                except Exception as exc:
                    self._report_cleanup_error(f"CH{channel} 电压恢复", exc)
                try:
                    self.n6705c.set_mode(channel, state["mode"])
                    self.log_fn(f"[INFO] CH{channel} 模式已恢复测试前设定: {state['mode']}")
                except Exception as exc:
                    self._report_cleanup_error(f"CH{channel} 模式恢复", exc)
                try:
                    if state["enabled"]:
                        self.n6705c.channel_on(channel)
                    else:
                        self.n6705c.channel_off(channel)
                    output_text = "ON" if state["enabled"] else "OFF"
                    self.log_fn(f"[INFO] CH{channel} 输出状态已恢复测试前设定: {output_text}")
                except Exception as exc:
                    self._report_cleanup_error(f"CH{channel} 输出状态恢复", exc)

    def _report_cleanup_error(self, action, exc):
        logger.error("GPADC %s失败: %s", action, exc, exc_info=True)
        self.log_fn(f"[ERROR] {action}失败: {exc}，请手动确认仪器状态")
        self.status_fn(f"错误: {action}失败，请手动确认仪器状态", True)

    @staticmethod
    def _voltage_channels_for_test(kind, config):
        if kind in ("force_voltage", "linearity_traverse", "temp_consistency", "ft_calib_check"):
            return [config["voltage_channel"]]
        if kind == "multi_ch_temp":
            channels = []
            for channel in config["channels"]:
                if channel.get("enabled", True) and channel.get("sweep_enabled"):
                    voltage_channel = int(channel.get("voltage_channel") or 1)
                    if voltage_channel not in channels:
                        channels.append(voltage_channel)
            return channels
        return []

    def _run_1000cnt(self, config, stop_check):
        if self.acquisition.mode == "UART":
            self.log_fn(
                f"[INFO] Starting 1000CNT TEST via UART Log, keyword='{self.acquisition.keyword}', "
                f"count={config['sample_cnt']}"
            )
        else:
            self.log_fn(
                f"[INFO] Starting 1000CNT TEST with I2C address: 0x{config['device_addr']:x} "
                f"Register: 0x{config['reg_addr']:x}, count={config['sample_cnt']}"
            )
        _, _, _, raw_data = self.acquisition.read_by_cnts(
            device_addr=config["device_addr"],
            reg_addr=config["reg_addr"],
            iic_weight=config["iic_weight"],
            get_reg_cnt=config["sample_cnt"],
            return_raw=True,
            stop_check=stop_check,
            progress_callback=self.progress_callback,
        )
        stats = compute_detailed_stats(raw_data)
        stats["raw"] = raw_data
        stats["algo_effect"] = self.acquisition.last_algo_effect
        stats["raw_before_algo"] = self.acquisition.last_raw_before_algo
        return "1000cnt", stats

    def _check_sweep_response(self, voltage_data, adc_mean):
        count = self.sweep_guard_points
        if len(adc_mean) < count or len(voltage_data) < count:
            return None
        head_v = voltage_data[:count]
        head_m = adc_mean[:count]
        spread = max(head_m) - min(head_m)
        net = head_m[-1] - head_m[0]
        detail = (
            f"前{count}点 V={[f'{v:.2f}' for v in head_v]}, "
            f"RawMean={[f'{m:.1f}' for m in head_m]}, "
            f"极差={spread:.1f} LSB, 净变化={net:+.1f} LSB"
        )
        if head_v[-1] > head_v[0] and net <= 0:
            return f"电压上升但 Raw 均值无净增量（疑似通道/地址/接线错误）。{detail}"
        if spread < self.sweep_guard_min_spread_lsb:
            return f"Raw 均值几乎不随电压变化（疑似 DUT 无响应或电压未施加）。{detail}"
        return None

    def _run_force_voltage(self, config, stop_check):
        self.log_fn(
            f"[INFO] Running FORCE VOLTAGE TEST with I2C address: 0x{config['device_addr']:x}, "
            f"Register: 0x{config['reg_addr']:x}"
        )
        if not self.mock_mode and (self.n6705c is None or not self.n6705c_connected):
            self.log_fn("[ERROR] N6705C not connected")
            self.status_fn("错误: N6705C未连接", True)
            return "force_voltage", None

        result, _ = self._sweep_force_voltage(config, stop_check)
        if result is not None:
            self.log_fn("===== FORCE VOLTAGE TEST 结果 =====")
        return "force_voltage", result

    def _sweep_force_voltage(
        self, config, stop_check, progress_callback=None, context="Force voltage test",
    ):
        """执行一次完整电压扫描，返回 (结果, 是否完整)，供单次及线性度遍历复用。"""
        settle_time = 0.0 if self.mock_mode else 0.5
        step_time = 0.0 if self.mock_mode else 0.2
        voltage_data, adc_mean, adc_min, adc_max = [], [], [], []
        raw_samples, raw_before_samples = [], []
        voltage_min = config["voltage_min"]
        voltage_max = config["voltage_max"]
        voltage_step = config["voltage_step"]
        channel = config["voltage_channel"]
        notify_progress = self.progress_callback if progress_callback is None else progress_callback

        self.n6705c.set_voltage(channel, voltage_min)
        time.sleep(settle_time)
        current_voltage = voltage_min
        total_points = max(1, int(round((voltage_max - voltage_min) / voltage_step)) + 1)
        point_idx = 0
        completed = True
        while current_voltage <= voltage_max + voltage_step * 0.001:
            if stop_check and stop_check():
                self.log_fn(f"[INFO] {context} stopped by user.")
                completed = False
                break
            self.n6705c.set_voltage(channel, current_voltage)
            time.sleep(step_time)
            avg, max_val, min_val, point_raw = self.acquisition.read_by_cnts(
                config["device_addr"], config["reg_addr"], config["iic_weight"],
                get_reg_cnt=config["sample_cnt"], return_raw=True, stop_check=stop_check,
            )
            point_before = self.acquisition.last_raw_before_algo
            voltage_data.append(current_voltage)
            adc_mean.append(avg)
            adc_min.append(min_val)
            adc_max.append(max_val)
            raw_samples.append(list(point_raw))
            raw_before_samples.append(list(point_before) if point_before is not None else None)

            if len(adc_mean) == self.sweep_guard_points:
                guard_reason = self._check_sweep_response(voltage_data, adc_mean)
                if guard_reason is not None:
                    self.log_fn(f"[WARN] GPADC response guard: {guard_reason}")
                    self.log_fn(f"[WARN] {context} 已中止，请检查 DUT 供电/接线/通道与采集配置")
                    self.status_fn("警告: GPADC 无响应，测试已提前中止", True)
                    return None, False

            current_voltage = round(current_voltage + voltage_step, 6)
            point_idx += 1
            notify_progress(int(point_idx * 100 / total_points))

        return {
            "voltage": voltage_data,
            "mean": adc_mean,
            "min": adc_min,
            "max": adc_max,
            "raw_samples": raw_samples,
            "raw_before_samples": raw_before_samples,
        }, completed

    def _evaluate_linearity_auto_candidate(
            self, config, value, repeat, stop_check, progress_offset, progress_total):
        device_addr = config["device_addr"]
        n_reg = config["linearity_n_reg_addr"]
        p_reg = config["linearity_p_reg_addr"]
        width = config["iic_weight"]
        self.acquisition.write_reg(device_addr, n_reg, value, width)
        self.acquisition.write_reg(device_addr, p_reg, value, width)
        pair_label = f"N=0x{value:X}, P=0x{value:X}"
        repeat_groups = []
        for repeat_index in range(repeat):
            if stop_check and stop_check():
                return None, "stopped"
            self.log_fn(f"[INFO] Auto Best {pair_label}, Repeat {repeat_index + 1}/{repeat}")

            def _repeat_progress(progress, _repeat_index=repeat_index):
                progress = min(100, max(0, int(progress))) / 100
                completed = progress_offset + _repeat_index + progress
                self.progress_callback(min(99, int(completed * 100 / progress_total)))

            sweep, completed = self._sweep_force_voltage(
                config,
                stop_check,
                progress_callback=_repeat_progress,
                context=f"Auto Best {pair_label} Repeat {repeat_index + 1}",
            )
            if sweep is None:
                return None, "failed"
            if not completed:
                return None, "stopped"
            group = analyze_linearity_group(
                value, value, sweep, calib_points=self.calib_points,
            )
            repeat_groups.append(group)
            self.log_fn(
                f"[RESULT] {pair_label}, Repeat {repeat_index + 1}, "
                f"Max Abs Error={group['max_abs_mv']:.2f} mV, "
                f"RMS Error={group['rms_mv']:.2f} mV"
            )
        return aggregate_linearity_repeats(repeat_groups), "complete"

    def _run_linearity_auto_best(self, config, stop_check):
        repeat = int(config.get("linearity_auto_repeat", 3))
        if not 1 <= repeat <= 10:
            raise ValueError("Linearity Auto Repeat must be between 1 and 10")
        low, high = normalize_linearity_auto_range(
            config["linearity_value_start"], config["linearity_value_end"],
        )
        range_start, range_end = low, high
        point_count = high - low + 1
        max_candidates = (2 + max(1, math.ceil(math.log2(point_count)))) if point_count > 1 else 1
        progress_total = max_candidates * repeat
        progress_offset = 0
        cache = {}
        evaluated_values = []
        comparisons = []
        ambiguous = False
        stopped = False
        converged = False
        self.log_fn(
            f"[INFO] Auto Best binary search: 0x{low:X} ~ 0x{high:X}, "
            f"Repeat={repeat}, median metrics"
        )

        while True:
            if stop_check and stop_check():
                stopped = True
                break
            step = advance_linearity_auto_best(low, high, cache)
            low, high = step["low"], step["high"]
            comparison = step["comparison"]
            if comparison is not None:
                comparisons.append(comparison)
                if comparison["ambiguous"]:
                    ambiguous = True
                self.log_fn(
                    f"[AUTO] Compare 0x{comparison['left_value']:X} / "
                    f"0x{comparison['right_value']:X}, "
                    f"mid=0x{comparison['mid_value']:X}: "
                    f"direction={comparison['direction']}, "
                    f"noise_tie={comparison['ambiguous']}"
                )
            if step["done"]:
                converged = True
                break
            value = step["evaluate_value"]
            if value is None:
                continue
            group, status = self._evaluate_linearity_auto_candidate(
                config, value, repeat, stop_check, progress_offset, progress_total,
            )
            if status == "failed":
                return None
            if status == "stopped":
                stopped = True
                break
            progress_offset += repeat
            cache[value] = group
            evaluated_values.append(value)
            self.log_fn(
                f"[RESULT] Auto candidate N=0x{value:X}, P=0x{value:X}, "
                f"Median Max Abs={group['max_abs_mv']:.2f} mV, "
                f"Median RMS={group['rms_mv']:.2f} mV, "
                f"Max Range={group['max_abs_range_mv']:.2f} mV"
            )

        groups = [cache[value] for value in sorted(cache)]
        auto_search = {
            "start": range_start,
            "end": range_end,
            "evaluated_values": evaluated_values,
            "terminal_value": None,
            "comparisons": comparisons,
            "ambiguous": ambiguous,
            "completed": converged,
        }
        return groups, stopped, auto_search

    def _run_linearity_traverse(self, config, stop_check):
        link_np = bool(config["linearity_link_np"])
        auto_best = link_np and bool(config.get("linearity_auto_best", False))
        self.log_fn(
            f"[INFO] Running LINEARITY TRAVERSE with I2C address: 0x{config['device_addr']:x}, "
            f"Raw Register: 0x{config['reg_addr']:x}, "
            f"N Register: 0x{config['linearity_n_reg_addr']:x}, "
            f"P Register: 0x{config['linearity_p_reg_addr']:x}, "
            f"Mode: {'Link N = P' if link_np else 'Independent N/P Matrix'}"
        )
        if self.acquisition.mode != "IIC":
            self.log_fn("[ERROR] Linearity Traverse requires I2C acquisition")
            self.status_fn("错误: Linearity Traverse 仅支持 I2C 采集", True)
            return "linearity_traverse", None
        if not self.mock_mode and (self.n6705c is None or not self.n6705c_connected):
            self.log_fn("[ERROR] N6705C not connected")
            self.status_fn("错误: N6705C未连接", True)
            return "linearity_traverse", None

        weight_pairs = None if auto_best else generate_linearity_pairs(config)
        device_addr = config["device_addr"]
        n_reg = config["linearity_n_reg_addr"]
        p_reg = config["linearity_p_reg_addr"]
        width = config["iic_weight"]
        original_n = self.acquisition.read_reg(device_addr, n_reg, width)
        original_p = self.acquisition.read_reg(device_addr, p_reg, width)
        self.log_fn(f"[INFO] Original N=0x{int(original_n):X}, P=0x{int(original_p):X}")
        groups = []
        stopped = False
        auto_search = None
        try:
            if auto_best:
                auto_result = self._run_linearity_auto_best(config, stop_check)
                if auto_result is None:
                    return "linearity_traverse", None
                groups, stopped, auto_search = auto_result
            else:
                total_groups = len(weight_pairs)
                for group_idx, (n_value, p_value) in enumerate(weight_pairs):
                    if stop_check and stop_check():
                        stopped = True
                        self.log_fn("[INFO] Linearity Traverse stopped by user.")
                        break
                    self.acquisition.write_reg(device_addr, n_reg, n_value, width)
                    self.acquisition.write_reg(device_addr, p_reg, p_value, width)
                    pair_label = f"N=0x{n_value:X}, P=0x{p_value:X}"
                    self.log_fn(
                        f"[INFO] Linearity {pair_label} ({group_idx + 1}/{total_groups})"
                    )

                    def _group_progress(value, _group_idx=group_idx):
                        value = min(100, max(0, int(value)))
                        self.progress_callback(
                            int((_group_idx * 100 + value) * 100 / (total_groups * 100))
                        )

                    sweep, completed = self._sweep_force_voltage(
                        config,
                        stop_check,
                        progress_callback=_group_progress,
                        context=f"Linearity Traverse {pair_label}",
                    )
                    if sweep is None:
                        return "linearity_traverse", None
                    if not completed:
                        stopped = True
                        break
                    group = analyze_linearity_group(
                        n_value, p_value, sweep, calib_points=self.calib_points,
                    )
                    groups.append(group)
                    self.log_fn(
                        f"[RESULT] {pair_label}, "
                        f"Max Abs Error={group['max_abs_mv']:.2f} mV, "
                        f"RMS Error={group['rms_mv']:.2f} mV"
                    )
        finally:
            try:
                self.acquisition.write_reg(device_addr, p_reg, int(original_p), width)
                self.log_fn(f"[INFO] P Weight restored to original value: 0x{int(original_p):X}")
            except Exception as exc:
                self._report_cleanup_error("P Weight 寄存器恢复", exc)
            try:
                self.acquisition.write_reg(device_addr, n_reg, int(original_n), width)
                self.log_fn(f"[INFO] N Weight restored to original value: 0x{int(original_n):X}")
            except Exception as exc:
                self._report_cleanup_error("N Weight 寄存器恢复", exc)

        best_index = select_best_linearity_group(groups, noise_aware=auto_best)
        if best_index is not None:
            best = groups[best_index]
            if auto_search is not None and auto_search["completed"]:
                auto_search["terminal_value"] = best["n_value"]
            self.log_fn(
                f"[RESULT] Best evaluated N=0x{best['n_value']:X}, P=0x{best['p_value']:X}, "
                f"Max Abs Error={best['max_abs_mv']:.2f} mV, "
                f"RMS Error={best['rms_mv']:.2f} mV"
            )
        if auto_best and not stopped:
            self.progress_callback(100)
        return "linearity_traverse", {
            "voltage": list(groups[0]["raw"]["voltage"]) if groups else [],
            "groups": groups,
            "best_index": best_index,
            "stopped": stopped,
            "original_n": int(original_n),
            "original_p": int(original_p),
            "auto_search": auto_search,
            "linearity": {
                "n_reg_addr": n_reg,
                "p_reg_addr": p_reg,
                "link_np": link_np,
                "auto_best": auto_best,
                "auto_repeat": config.get("linearity_auto_repeat", 3),
                "start": config.get("linearity_start"),
                "end": config.get("linearity_end"),
                "value_start": config.get("linearity_value_start"),
                "value_end": config.get("linearity_value_end"),
                "value_step": config.get("linearity_value_step"),
                "n_start": config.get("linearity_n_start"),
                "n_end": config.get("linearity_n_end"),
                "n_value_start": config.get("linearity_n_value_start"),
                "n_value_end": config.get("linearity_n_value_end"),
                "n_value_step": config.get("linearity_n_value_step"),
                "p_start": config.get("linearity_p_start"),
                "p_end": config.get("linearity_p_end"),
                "p_value_start": config.get("linearity_p_value_start"),
                "p_value_end": config.get("linearity_p_value_end"),
                "p_value_step": config.get("linearity_p_value_step"),
            },
        }

    def _run_high_low_temp(self, config, stop_check):
        self.log_fn("[INFO] RUN TEST_HIGH_LOW_TEMP TEST")
        if not self.mock_mode and (self.chamber is None or not self.chamber_connected):
            self.log_fn("[ERROR] Chamber not connected")
            self.status_fn("错误: 温箱未连接", True)
            return "high_low_temp", None
        monitor_enabled = bool(config.get("current_monitor_enabled", False))
        monitor_channel = int(config.get("current_monitor_channel", 1))
        if monitor_enabled and not self.mock_mode and (
                self.n6705c is None or not self.n6705c_connected):
            self.log_fn("[ERROR] N6705C not connected for current monitoring")
            self.status_fn("错误: 电流监控需要连接 N6705C", True)
            return "high_low_temp", None
        if monitor_enabled:
            self.log_fn(f"[INFO] Current monitoring enabled: N6705C CH{monitor_channel}")

        device = None if self.acquisition.mode == "UART" else self.acquisition.ensure_i2c()
        if device is not None:
            test_data = device.read(config["device_addr"], config["reg_addr"], config["iic_weight"])
            self.log_fn(f"[INFO] Test data: {test_data:x}")

        temp_data, adc_mean, adc_min, adc_max = [], [], [], []
        current_data = []
        current_temp = config["temp_min"]
        total_points = max(1, int(round((config["temp_max"] - config["temp_min"]) / config["temp_step"])) + 1)
        point_idx = 0
        try:
            while current_temp <= config["temp_max"] + 0.001:
                if stop_check and stop_check():
                    self.log_fn("[INFO] High/Low temp test stopped by user.")
                    break
                try:
                    self.chamber.set_temperature(current_temp)
                    self.status_fn(f"设置温箱温度到 {current_temp:.1f}°C", False)
                    if self.mock_mode:
                        self.log_fn(f"[DEBUG] Temp set to {current_temp:.1f}°C (instant)")
                    else:
                        if point_idx == 0:
                            try:
                                self.chamber.start()
                                self.log_fn("[INFO] Chamber started (constant-temp run command sent)")
                            except Exception as exc:
                                self.log_fn(f"[WARN] Chamber start command failed: {exc}")
                        stabilizer = TemperatureStabilizer(
                            self.chamber, log_fn=self.log_fn, stop_check=stop_check,
                            max_read_failures=12,
                        )
                        stable = stabilizer.wait_for_stable(current_temp)
                        if stable.reason == "stopped":
                            self.log_fn("[INFO] High/Low temp test stopped by user.")
                            break
                        actual_str = "N/A" if stable.actual is None else f"{stable.actual:.2f}"
                        self.log_fn(
                            f"[INFO] Temperature {stable.reason}: target={current_temp:.1f}, "
                            f"actual={actual_str}, waited {stable.waited_s:.0f}s, polls={stable.poll_count}"
                        )
                        self.status_fn(f"DUT温度均衡中: {current_temp:.1f}°C", False)
                        for _ in range(int(config["soak_time"])):
                            if stop_check and stop_check():
                                break
                            time.sleep(1)
                        if stop_check and stop_check():
                            self.log_fn("[INFO] High/Low temp test stopped by user.")
                            break

                    if self.mock_mode:
                        self.acquisition.mock_i2c.set_mock_voltage(current_temp / 100.0)
                    avg, max_val, min_val, _ = self.acquisition.read_by_cnts(
                        config["device_addr"], config["reg_addr"], config["iic_weight"],
                        get_reg_cnt=config["sample_cnt"], return_raw=True, stop_check=stop_check,
                    )
                except Exception as exc:
                    logger.warning("高低温测试温度点 %.1f°C 执行失败: %s", current_temp, exc, exc_info=True)
                    if self.mock_mode or self.confirm_fn is None:
                        raise
                    answered, retry = self.confirm_fn(
                        "温箱通信失败",
                        f"温度点 {current_temp:.1f}°C 执行失败：\n{exc}\n\n"
                        "常见原因：USB 串口转换器瞬时掉线、端口被其它程序占用、USB 电源管理挂起。\n"
                        "请检查温箱串口连接并恢复环境后：\n"
                        "· 【重试】重新打开串口，重测当前温度点（已测数据保留）\n"
                        "· 【中止】结束测试，输出已测温度点数据",
                    )
                    if not answered:
                        self.log_fn("[INFO] High/Low temp test stopped by user.")
                    elif not retry:
                        self.log_fn(
                            f"[WARN] 温度点 {current_temp:.1f}°C 执行失败且未重试，测试提前结束（已测数据保留）"
                        )
                    if not retry:
                        break
                    try:
                        self.chamber.disconnect()
                        self.chamber.connect()
                        self.log_fn("[INFO] 温箱串口已重新打开，重试当前温度点")
                    except Exception as reconnect_exc:
                        self.log_fn(f"[WARN] 温箱串口重开失败: {reconnect_exc}")
                        logger.warning("温箱串口重开失败", exc_info=True)
                    continue

                current_a = None
                if monitor_enabled:
                    try:
                        current_a = float(self.n6705c.measure_current(monitor_channel))
                    except Exception as exc:
                        logger.error(
                            "GPADC 电流监控读取 CH%s 失败: %s", monitor_channel, exc,
                            exc_info=True,
                        )
                        self.log_fn(f"[ERROR] 读取 N6705C CH{monitor_channel} 电流失败: {exc}")
                        self.status_fn("错误: N6705C 电流读取失败", True)
                        raise

                temp_data.append(current_temp)
                adc_mean.append(avg)
                adc_min.append(min_val)
                adc_max.append(max_val)
                if monitor_enabled:
                    current_data.append(current_a)
                point_log = f"[INFO] T={current_temp:.1f}°C, avg={avg:.2f}, min={min_val}, max={max_val}"
                if monitor_enabled:
                    point_log += f", CH{monitor_channel} current={current_a:.2e} A"
                self.log_fn(point_log)
                current_temp += config["temp_step"]
                point_idx += 1
                self.progress_callback(int(point_idx * 100 / total_points))
                time.sleep(1)
        finally:
            try:
                self.chamber.set_temperature(25.0)
            except Exception as exc:
                self._report_cleanup_error("恢复温箱 25°C", exc)

        self.log_fn("===== HIGH/LOW TEMP TEST 结果 =====")
        result_headers = ["Temp", "RawMean", "RawMin", "RawMax"]
        if monitor_enabled:
            result_headers.append(f"CH{monitor_channel} Current (A)")
        result_rows = []
        for index in range(len(temp_data)):
            row = [
                f"{temp_data[index]:.2f}", f"{adc_mean[index]:.2f}",
                str(adc_min[index]), str(adc_max[index]),
            ]
            if monitor_enabled:
                row.append(f"{current_data[index]:.2e}")
            result_rows.append(row)
        for line in format_log_table(result_headers, result_rows):
            self.log_fn("[DATA] " + line)
        result = {
            "voltage": temp_data, "mean": adc_mean, "min": adc_min, "max": adc_max,
        }
        if monitor_enabled:
            result["current_a"] = current_data
            result["current_channel"] = monitor_channel
        return "high_low_temp", result

    def _calibration_data(self, result):
        k, b, mean_cali, min_cali, max_cali, v_low, m_low, v_high, m_high = compute_calibration(
            result["voltage"], result["mean"], result["min"], result["max"],
            calib_points=self.calib_points,
        )
        if k == 0.0:
            self.log_fn("[WARN] 标定斜率 k=0（ADC 读数无变化或采样点电压相同），跳过标定，使用原始数据")
        self.log_fn(f"[INFO] Calibration: k={k:.2f} (LSB/V), b={b:.2f} (LSB)")
        cali_headers = ["Voltage", "RawMean", "mean_cali", "Δmean(mV)", "RawMin",
                        "RawMax", "min_cali", "max_cali", "Δmin(mV)", "Δmax(mV)"]
        cali_rows = []
        for index, input_voltage in enumerate(result["voltage"]):
            delta_mean_mv = (mean_cali[index] - input_voltage) * 1000
            delta_min_mv = (min_cali[index] - input_voltage) * 1000
            delta_max_mv = (max_cali[index] - input_voltage) * 1000
            cali_rows.append([
                f"{input_voltage:.2f}", f"{result['mean'][index]:.2f}",
                f"{mean_cali[index]:.2f}", f"{delta_mean_mv:+.2f}",
                str(result['min'][index]), str(result['max'][index]),
                f"{min_cali[index]:.2f}", f"{max_cali[index]:.2f}",
                f"{delta_min_mv:+.2f}", f"{delta_max_mv:+.2f}",
            ])
        for line in format_log_table(cali_headers, cali_rows):
            self.log_fn("[DATA] " + line)
        self.log_fn(
            f"[INFO] calibration points: v_low={v_low:.2f}, m_low={m_low:.2f}, "
            f"v_high={v_high:.2f}, m_high={m_high:.2f}"
        )
        self.log_fn(f"[INFO] Calibration: k={k:.2f} (LSB/V), b={b:.2f} (LSB)")
        return mean_cali, min_cali, max_cali

    def _run_temp_consistency(self, config, stop_check):
        self.log_fn("[INFO] RUN TEST_TEMP_CONSISTENCY TEST")
        self.log_fn(
            f"[INFO] Running TEMP CONSISTENCY TEST with I2C address: 0x{config['device_addr']:x}, "
            f"Register: 0x{config['reg_addr']:x}"
        )
        if not self.mock_mode:
            if self.chamber is None or not self.chamber_connected:
                self.log_fn("[ERROR] Chamber not connected")
                self.status_fn("错误: 温箱未连接", True)
                return "temp_consistency", None
            if self.n6705c is None or not self.n6705c_connected:
                self.log_fn("[ERROR] N6705C not connected")
                self.status_fn("错误: N6705C未连接", True)
                return "temp_consistency", None
            if self.acquisition.mode != "UART":
                self.acquisition.ensure_i2c()

        settle_time = 0.0 if self.mock_mode else 0.5
        step_time = 0.0 if self.mock_mode else 0.2
        voltage_points = []
        voltage = config["voltage_min"]
        while voltage <= config["voltage_max"] + config["voltage_step"] * 0.001:
            voltage_points.append(round(voltage, 6))
            voltage = round(voltage + config["voltage_step"], 6)

        temp_list, mean_matrix, min_matrix, max_matrix = [], [], [], []
        total_temp_points = max(1, int(round((config["temp_max"] - config["temp_min"]) / config["temp_step"])) + 1)
        total_steps = total_temp_points * len(voltage_points)
        completed_steps = 0
        current_temp = config["temp_min"]
        while current_temp <= config["temp_max"] + 0.001:
            if stop_check and stop_check():
                self.log_fn("[INFO] Temp consistency test stopped by user.")
                break
            self.chamber.set_temperature(current_temp)
            self.status_fn(f"设置温箱温度到 {current_temp:.1f}°C", False)
            if self.mock_mode:
                self.log_fn(f"[DEBUG] Temp set to {current_temp:.1f}°C (instant)")
            else:
                history, stable_count = [], 0
                while True:
                    if stop_check and stop_check():
                        break
                    actual_temp = self.chamber.get_current_temp()
                    history.append(actual_temp)
                    if len(history) > 10:
                        history.pop(0)
                    if len(history) >= 5:
                        stable_count = stable_count + 1 if max(history) - min(history) < 0.2 else 0
                        if stable_count >= 3:
                            break
                    self.log_fn(f"[INFO] Temp stabilizing: target={current_temp:.1f}, actual={actual_temp:.2f}")
                    for _ in range(30):
                        if stop_check and stop_check():
                            break
                        time.sleep(1)
                if stop_check and stop_check():
                    self.log_fn("[INFO] Temp consistency test stopped by user.")
                    break
                self.status_fn(f"DUT温度均衡中: {current_temp:.1f}°C", False)
                for _ in range(int(config["soak_time"])):
                    if stop_check and stop_check():
                        break
                    time.sleep(1)
                if stop_check and stop_check():
                    self.log_fn("[INFO] Temp consistency test stopped by user.")
                    break

            mean_row, min_row, max_row = [], [], []
            self.n6705c.set_voltage(config["voltage_channel"], config["voltage_min"])
            time.sleep(settle_time)
            for voltage_point in voltage_points:
                if stop_check and stop_check():
                    break
                self.n6705c.set_voltage(config["voltage_channel"], voltage_point)
                time.sleep(step_time)
                avg, max_val, min_val = self.acquisition.read_by_cnts(
                    config["device_addr"], config["reg_addr"], config["iic_weight"],
                    get_reg_cnt=config["sample_cnt"], return_raw=False, stop_check=stop_check,
                )
                mean_row.append(avg)
                min_row.append(min_val)
                max_row.append(max_val)
                completed_steps += 1
                self.progress_callback(int(completed_steps * 100 / total_steps))
            if stop_check and stop_check():
                break
            temp_list.append(current_temp)
            mean_matrix.append(mean_row)
            min_matrix.append(min_row)
            max_matrix.append(max_row)
            self.log_fn(f"[INFO] T={current_temp:.1f}°C  voltage sweep done ({len(mean_row)} points)")
            current_temp = round(current_temp + config["temp_step"], 6)

        voltage_headers = [f"{voltage:.2f}" for voltage in voltage_points]
        for title, matrix in (("Mean", mean_matrix), ("Min", min_matrix), ("Max", max_matrix)):
            self.log_fn(f"===== TEMP CONSISTENCY TEST 结果 ({title}) =====")
            rows = [
                [f"T={temp:.1f}"] + [f"{value:.2f}" for value in matrix[index]]
                for index, temp in enumerate(temp_list) if index < len(matrix)
            ]
            for line in format_log_table(["Temp\\Voltage"] + voltage_headers, rows, sep="  "):
                self.log_fn("[DATA] " + line)

        mean_cali_matrix, min_cali_matrix, max_cali_matrix = [], [], []
        for index in range(len(temp_list)):
            if index < len(mean_matrix):
                mean_cali, min_cali, max_cali = self._calibration_data({
                    "voltage": voltage_points,
                    "mean": mean_matrix[index],
                    "min": min_matrix[index],
                    "max": max_matrix[index],
                })
                mean_cali_matrix.append(mean_cali)
                min_cali_matrix.append(min_cali)
                max_cali_matrix.append(max_cali)

        for title, matrix in (
            ("Mean Cali", mean_cali_matrix), ("Min Cali", min_cali_matrix), ("Max Cali", max_cali_matrix),
        ):
            self.log_fn(f"===== TEMP CONSISTENCY TEST 校准结果 ({title}) =====")
            rows = [
                [f"T={temp:.1f}"] + [f"{value:.2f}" for value in matrix[index]]
                for index, temp in enumerate(temp_list) if index < len(matrix)
            ]
            for line in format_log_table(["Temp\\Voltage"] + voltage_headers, rows, sep="  "):
                self.log_fn("[DATA] " + line)
        return "temp_consistency", {
            "temp": temp_list,
            "voltage": voltage_points,
            "mean": mean_matrix,
            "min": min_matrix,
            "max": max_matrix,
            "mean_cali": mean_cali_matrix,
            "min_cali": min_cali_matrix,
            "max_cali": max_cali_matrix,
        }

    def _run_multi_ch_temp(self, config, stop_check):
        self.log_fn("[INFO] RUN TEST_MULTI_CH_TEMP TEST")
        if not self.mock_mode:
            if self.chamber is None or not self.chamber_connected:
                self.log_fn("[ERROR] Chamber not connected")
                self.status_fn("错误: 温箱未连接", True)
                return None
            need_sweep = any(
                channel.get("enabled", True) and channel.get("sweep_enabled")
                for channel in config["channels"]
            )
            if need_sweep and (self.n6705c is None or not self.n6705c_connected):
                self.log_fn("[ERROR] N6705C not connected")
                self.status_fn("错误: N6705C未连接", True)
                return None
            if self.acquisition.mode == "UART" and any(
                (channel.get("switch_writes_text") or channel.get("switch_writes"))
                for channel in config["channels"] if channel.get("enabled", True)
            ):
                self.log_fn("[INFO] UART 采集模式下，通道切换仍经 I2C 接口写入")

        def sample_fn(channel_config, count, stop, mock_hint=None):
            dev = parse_hw_int(channel_config.get("read_dev"), config["device_addr"])
            reg = parse_hw_int(channel_config.get("read_reg"), config["reg_addr"])
            width = int(channel_config.get("read_width") or 0) or config["iic_weight"]
            if self.mock_mode and mock_hint is not None:
                self.acquisition.mock_i2c.set_mock_voltage(mock_hint)
            return self.acquisition.read_by_cnts(
                dev, reg, width, get_reg_cnt=count, return_raw=False, stop_check=stop,
            )

        result = run_multi_ch_temp_test(
            chamber=self.chamber,
            vol_source=self.n6705c,
            write_fn=self.acquisition.write_reg,
            read_reg_fn=self.acquisition.read_reg,
            sample_fn=sample_fn,
            channels=config["channels"],
            pre_config=config["pre_config"],
            temp_min=config["temp_min"],
            temp_max=config["temp_max"],
            temp_step=config["temp_step"],
            soak_time=config["soak_time"],
            sample_cnt=config["sample_cnt"],
            default_dev=config["device_addr"],
            default_width=config["iic_weight"],
            mock_mode=self.mock_mode,
            log_fn=self.log_fn,
            status_fn=self.status_fn,
            stop_check=stop_check,
            progress_callback=self.progress_callback,
        )
        # sample_cnt 为扩算后的原始采样数；points 还原为最终测试点数供导出
        result["points"] = config["sample_cnt"] // algorithm_length_divisor(self.acquisition.algorithm)
        return "multi_ch_temp", result

    def _run_ft_calib_check(self, config, stop_check):
        mode = self.acquisition.mode
        self.log_fn(f"[INFO] RUN FT CALIBRATION CHECK ({mode})")
        if not self.mock_mode and (self.n6705c is None or not self.n6705c_connected):
            self.log_fn("[ERROR] N6705C not connected")
            self.status_fn("错误: N6705C未连接", True)
            return None
        if self.acquisition.algorithm is not None:
            self.log_fn("[INFO] FT Calibration Check 不应用采样算法，已忽略 Algorithm 配置")
        if self.acquisition.outlier_filter is not None:
            self.log_fn("[INFO] FT Calibration Check 不应用离群样本筛选，已忽略 Outlier Filter 配置")

        def set_voltage(voltage):
            self.n6705c.set_voltage(config["voltage_channel"], voltage)
            if self.mock_mode:
                self.acquisition.mock_i2c.set_mock_voltage(voltage / config["divider_ratio"])

        def sample_iic(count, stop):
            return self.acquisition.reg_read_by_cnts(
                config["device_addr"], config["reg_addr"], config["iic_weight"],
                get_reg_cnt=count, return_raw=False, stop_check=stop,
            )

        def sample_uart(count, stop):
            return self.acquisition.uart_read_raw_volt_by_cnts(
                get_reg_cnt=count, keyword=self.acquisition.keyword, stop_check=stop,
            )

        with self.acquisition.processing_disabled():
            result = run_ft_calib_check(
                mode=mode,
                calib_p1=config["calib_p1"],
                calib_p2=config["calib_p2"],
                raw_tol_lsb=config["raw_tol_lsb"],
                err_limit_mv=config["err_limit_mv"],
                divider_ratio=config["divider_ratio"],
                voltage_min=config["voltage_min"],
                voltage_max=config["voltage_max"],
                voltage_step=config["voltage_step"],
                sample_cnt=config["sample_cnt"],
                set_voltage_fn=set_voltage,
                sample_iic_fn=sample_iic,
                sample_uart_fn=sample_uart,
                settle_s=0.0 if self.mock_mode else 0.5,
                step_s=0.0 if self.mock_mode else 0.2,
                log_fn=self.log_fn,
                status_fn=self.status_fn,
                stop_check=stop_check,
                progress_callback=self.progress_callback,
            )
        if result is None:
            return None
        return "ft_calib_check", result
