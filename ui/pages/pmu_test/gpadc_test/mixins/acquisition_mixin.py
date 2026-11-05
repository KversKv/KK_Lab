"""GPADCTestUI UART / IIC 采集依赖装配与结果数据整形 Mixin。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来。
类装配见 gpadc_test_ui.py。"""

import queue
import time

from lib.i2c.i2c_interface_x64 import I2CInterface
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockI2C
from core.pmu_test.gpadc import GPADCAcquisition, compute_calibration


class _AcquisitionMixin:
    """UART 数据入队、core 采样器装配及兼容采样接口。"""

    def _on_uart_rx_data(self, data):
        """GUI 串口槽仅入队；解析、采样与算法均在 core runner 线程执行。"""
        self._uart_rx_queue.put(bytes(data))

    def _drain_uart_rx_queue(self):
        while True:
            try:
                self._uart_rx_queue.get_nowait()
            except queue.Empty:
                break

    def _next_uart_log_line(self, partial, deadline, stop_check=None):
        """兼容保留的纯队列读取接口，不操作 Widget。"""
        while b"\n" not in partial:
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

    def _create_gpadc_acquisition(self, *, log_fn, status_fn):
        """把控件快照与采集资源装配成无 UI 依赖的 core 采样器。"""
        mock_i2c = None
        if DEBUG_MOCK:
            if not hasattr(self, "_mock_i2c"):
                self._mock_i2c = MockI2C()
            mock_i2c = self._mock_i2c
        return GPADCAcquisition(
            mode=self._acq_mode_snapshot,
            keyword=self._uart_keyword_snapshot,
            uart_queue=self._uart_rx_queue,
            i2c=None if DEBUG_MOCK else getattr(self, "deviceI2C", None),
            i2c_factory=None if DEBUG_MOCK else I2CInterface,
            iic_speed=self._iic_speed_snapshot,
            mock_i2c=mock_i2c,
            mock_mode=DEBUG_MOCK,
            algorithm=self._algorithm_snapshot,
            outlier_filter=self._outlier_filter_snapshot,
            log_fn=log_fn,
            status_fn=status_fn,
        )

    def _compat_acquisition(self):
        worker = self._test_worker
        return self._create_gpadc_acquisition(
            log_fn=worker.log.emit if worker is not None else lambda message: None,
            status_fn=(worker.status.emit if worker is not None
                       else lambda message, is_error=False: None),
        )

    def _sync_acquisition_state(self, acquisition):
        self._last_algo_effect = acquisition.last_algo_effect
        self._last_raw_before_algo = acquisition.last_raw_before_algo

    def gpadc_uart_read_by_cnts(
        self,
        get_reg_cnt=1000,
        keyword="",
        timeout_s=120.0,
        return_raw=False,
        stop_check=None,
        progress_callback=None,
    ):
        acquisition = self._compat_acquisition()
        result = acquisition.uart_read_by_cnts(
            get_reg_cnt=get_reg_cnt,
            keyword=keyword,
            timeout_s=timeout_s,
            return_raw=return_raw,
            stop_check=stop_check,
            progress_callback=progress_callback,
        )
        self._sync_acquisition_state(acquisition)
        return result

    def gpadc_uart_read_raw_volt_by_cnts(
        self,
        get_reg_cnt=1000,
        keyword="",
        timeout_s=120.0,
        stop_check=None,
        progress_callback=None,
    ):
        acquisition = self._compat_acquisition()
        return acquisition.uart_read_raw_volt_by_cnts(
            get_reg_cnt=get_reg_cnt,
            keyword=keyword,
            timeout_s=timeout_s,
            stop_check=stop_check,
            progress_callback=progress_callback,
        )

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
        acquisition = self._compat_acquisition()
        result = acquisition.read_by_cnts(
            device_addr=device_addr,
            reg_addr=reg_addr,
            iic_weight=iic_weight,
            get_reg_cnt=get_reg_cnt,
            return_raw=return_raw,
            stop_check=stop_check,
            progress_callback=progress_callback,
        )
        self._sync_acquisition_state(acquisition)
        return result

    def _ensure_device_i2c(self):
        """兼容页面已有 IIC 访问点，并同步本次 IIC Speed 快照。"""
        if not hasattr(self, "deviceI2C"):
            self.deviceI2C = I2CInterface()
            self._test_worker.status.emit("I2C接口初始化成功", False)
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
        acquisition = self._compat_acquisition()
        result = acquisition.reg_read_by_cnts(
            device_addr=device_addr,
            reg_addr=reg_addr,
            iic_weight=iic_weight,
            get_reg_cnt=get_reg_cnt,
            return_raw=return_raw,
            stop_check=stop_check,
            progress_callback=progress_callback,
        )
        self._sync_acquisition_state(acquisition)
        return result

    def _apply_outlier_filter(self, raw_data):
        acquisition = self._compat_acquisition()
        return acquisition.apply_outlier_filter(raw_data)

    def _apply_algo_tracked(self, raw_data):
        acquisition = self._compat_acquisition()
        result = acquisition.apply_algorithm_tracked(raw_data)
        self._sync_acquisition_state(acquisition)
        return result

    def _calibration_data(self, result, log_fn=None):
        log = log_fn or self._append_log
        adc_raw_data = result["voltage"]
        adc_mean = result["mean"]
        adc_min = result["min"]
        adc_max = result["max"]

        k, b, mean_cali, adc_min_cali, adc_max_cali, v_low, m_low, v_high, m_high = \
            compute_calibration(
                adc_raw_data, adc_mean, adc_min, adc_max,
                calib_points=self._calib_points_snapshot,
            )

        if k == 0.0:
            log("[WARN] 标定斜率 k=0（ADC 读数无变化或采样点电压相同），跳过标定，使用原始数据")
        log(f"[INFO] Calibration: k={k:.6f} (LSB/V), b={b:.6f} (LSB)")
        log('Voltage,RawMean,mean_cali,Δmean(mV),RawMin,RawMax,min_cali,max_cali,Δmin(mV),Δmax(mV)')
        for i in range(len(adc_raw_data)):
            v_in = adc_raw_data[i]
            delta_mean_mv = (mean_cali[i] - v_in) * 1000
            delta_min_mv = (adc_min_cali[i] - v_in) * 1000
            delta_max_mv = (adc_max_cali[i] - v_in) * 1000
            log(
                f'{v_in:.4f},{adc_mean[i]:.3f},{mean_cali[i]:.6f},{delta_mean_mv:+.3f}'
                f',{adc_min[i]},{adc_max[i]}'
                f',{adc_min_cali[i]:.6f},{adc_max_cali[i]:.6f}'
                f',{delta_min_mv:+.3f},{delta_max_mv:+.3f}'
            )
        log(
            f"[INFO] calibration points: v_low={v_low:.4f}, m_low={m_low:.3f}, "
            f"v_high={v_high:.4f}, m_high={m_high:.3f}"
        )
        log(f"[INFO] Calibration: k={k:.6f} (LSB/V), b={b:.6f} (LSB)")
        return adc_raw_data, mean_cali, adc_min_cali, adc_max_cali

    def _compute_multi_ch_calibration(self, result):
        """多通道扫压结果逐温度行两点标定，供绘图与导出使用。"""
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
                n = min(len(vpts), len(mean_rows[i]))
                if n == 0:
                    mean_cali_rows.append([])
                    min_cali_rows.append([])
                    max_cali_rows.append([])
                    continue
                k, b, mean_cali, min_cali, max_cali, *_ = compute_calibration(
                    vpts[:n], mean_rows[i][:n],
                    (min_rows[i] if i < len(min_rows) else [])[:n],
                    (max_rows[i] if i < len(max_rows) else [])[:n],
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

    def _calculate_gpadc_parameters(self, force_voltage_result):
        """基于 force_voltage 返回值计算 GPADC 性能参数。"""
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

        coeffs = np.polyfit(voltage, adc_mean, 1)
        slope = coeffs[0]
        adc_ideal = np.polyval(coeffs, voltage)
        ss_res = np.sum((adc_mean - adc_ideal) ** 2)
        ss_tot = np.sum((adc_mean - np.mean(adc_mean)) ** 2)
        params['linearity'] = float(1.0 - ss_res / ss_tot) if ss_tot > 0 else 1.0

        inl_values = adc_mean - adc_ideal
        params['inl'] = float(np.max(np.abs(inl_values)))
        ideal_step = slope * (voltage[1] - voltage[0])
        actual_steps = np.diff(adc_mean)
        if ideal_step != 0:
            dnl_values = (actual_steps - ideal_step) / abs(ideal_step)
            params['dnl'] = float(np.max(np.abs(dnl_values)))
        else:
            params['dnl'] = 0.0

        noise_pp = adc_max - adc_min
        noise_rms = np.mean(noise_pp) / (2 * np.sqrt(3))
        adc_full_range = params['max'] - params['min']
        if noise_rms > 0 and adc_full_range > 0:
            snr_db = 20 * np.log10(adc_full_range / (noise_rms * 2 * np.sqrt(3)))
            params['enob'] = float(max(0.0, (snr_db - 1.76) / 6.02))
        else:
            params['enob'] = 0.0

        volt_range = float(voltage[-1] - voltage[0])
        adc_range = float(adc_mean[-1] - adc_mean[0])
        if volt_range > 0:
            ideal_slope = adc_range / volt_range
            params['gain_error'] = float(((slope - ideal_slope) / ideal_slope) * 100) if ideal_slope != 0 else 0.0
        else:
            params['gain_error'] = 0.0
        params['offset_error'] = float(adc_ideal[0] - adc_mean[0])
        self._append_log(
            f"[RESULT] INL={params['inl']:.3f}, DNL={params['dnl']:.3f}, "
            f"ENOB={params['enob']:.3f}, Gain Error: {params['gain_error']:.3f}%, "
            f"Offset Error: {params['offset_error']:.3f} LSB"
        )
        return params
