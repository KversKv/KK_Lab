"""GPADCTestUI 测试启停 / 编排 / Worker 生命周期 Mixin。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
类装配见 gpadc_test_ui.py。"""

from ui.styles import update_start_btn_state
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread
from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
from log_config import get_logger
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockChamber, MockI2C, MockN6705C
from ui.theme import apply_qss
from core.pmu_test.gpadc import (
    TestWorker as _TestWorker, compute_detailed_stats, run_ft_calib_check,
    ALGORITHM_REGISTRY, describe_algorithm, assess_fluctuation, parse_hw_int,
    run_multi_ch_temp_test
)

logger = get_logger(__name__)


class _ExecutionMixin:
    """测试启停 / 编排 / Worker 生命周期 Mixin"""

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._stop_test()
        else:
            self._start_test()

    def _start_test(self):
        if self.is_test_running:
            return

        self._acq_mode_snapshot = 'UART' if self.uart_radio.isChecked() else 'IIC'
        self._uart_keyword_snapshot = self.uart_keyword.text().strip()
        self._calib_points_snapshot = self._parse_calib_points()
        if self._calib_points_snapshot is not None:
            v_lo, v_hi = self._calib_points_snapshot
            self._append_log(f"[INFO] 使用手动校准点: low={v_lo}, high={v_hi}")
        self._algorithm_snapshot = self._collect_algorithm_config()
        if self._algorithm_snapshot is not None:
            self._append_log(f"[INFO] 启用采样算法: {describe_algorithm(self._algorithm_snapshot)}")
            _algo_spec = ALGORITHM_REGISTRY.get(self._algorithm_snapshot['id']) or {}
            if _algo_spec.get('principle'):
                self._append_log(f"[INFO] {_algo_spec['principle']}")
        self._iic_speed_snapshot = I2CSpeedMode(self.iic_speed_combo.currentData())
        if self.outlier_filter_switch.isChecked():
            self._outlier_filter_snapshot = {
                'pos': self.outlier_pos_offset.value(),
                'neg': self.outlier_neg_offset.value(),
            }
            self._append_log(
                f"[INFO] 启用离群样本筛选: 正向最大偏移 +{self._outlier_filter_snapshot['pos']:.1f} LSB, "
                f"负向最大偏移 -{self._outlier_filter_snapshot['neg']:.1f} LSB（以样本均值为基准）"
            )
        else:
            self._outlier_filter_snapshot = None
        if self._acq_mode_snapshot == 'UART':
            if not DEBUG_MOCK and not self._serial_connected:
                self._append_log("[ERROR] DUT 串口未连接，无法通过 UART Log 采集")
                self.set_system_status("错误: DUT串口未连接", is_error=True)
                return
            self._drain_uart_rx_queue()

        # 新测试开始：清除上一次的曲线与结果指标，避免新旧数据混显
        self._reset_result_display()

        self.is_test_running = True
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(True)
        self._test_stop_requested = False
        self._update_test_button_state(True)
        self._set_ui_enabled(False)
        self.set_progress(0)
        self._append_log(f"[INFO] Starting GPADC test... mode={self.current_test_item}")

        test_item = self.current_test_item
        iic_device_addr = int(self.iic_device_address.text(), 16)
        iic_reg_addr = int(self.iic_data_address.text(), 16)
        iic_width = self.iic_width_combo.currentData()
        sample_cnt = self.sample_count.value()

        if test_item == self.TEST_1000CNT:
            fn = self._run_1000cnt_test
            kwargs = dict(
                device_addr=iic_device_addr,
                reg_addr=iic_reg_addr,
                iic_weight=iic_width,
                sample_cnt=sample_cnt,
            )
        elif test_item == self.TEST_FORCE_VOLTAGE:
            fn = self._run_force_voltage_test
            kwargs = dict(
                device_addr=iic_device_addr,
                reg_addr=iic_reg_addr,
                iic_weight=iic_width,
                voltage_min=self.voltage_min.value(),
                voltage_max=self.voltage_max.value(),
                voltage_step=self.voltage_step.value(),
                voltage_channel=self.voltage_channel.currentData(),
                sample_cnt=sample_cnt,
            )
        elif test_item == self.TEST_HIGH_LOW_TEMP:
            fn = self._run_high_low_temp_test
            kwargs = dict(
                device_addr=iic_device_addr,
                reg_addr=iic_reg_addr,
                iic_weight=iic_width,
                temp_min=self.temp_min.value(),
                temp_max=self.temp_max.value(),
                temp_step=self.temp_step.value(),
                voltage_channel=self.voltage_channel.currentData(),
                soak_time=self.soak_time.value(),
                sample_cnt=sample_cnt,
            )
        elif test_item == self.TEST_TEMP_CONSISTENCY:
            fn = self._run_temp_consistency_test
            kwargs = dict(
                device_addr=iic_device_addr,
                reg_addr=iic_reg_addr,
                iic_weight=iic_width,
                temp_min=self.temp_min.value(),
                temp_max=self.temp_max.value(),
                temp_step=self.temp_step.value(),
                voltage_min=self.voltage_min.value(),
                voltage_max=self.voltage_max.value(),
                voltage_step=self.voltage_step.value(),
                voltage_channel=self.voltage_channel.currentData(),
                soak_time=self.soak_time.value(),
                sample_cnt=sample_cnt,
            )
        elif test_item == self.TEST_MULTI_CH_TEMP:
            channels = self.multi_ch_panel.get_channels()
            if not any(c.get('enabled', True) for c in channels):
                self._append_log("[ERROR] Multi-Ch Temp Test: 无已启用的通道")
                self.set_system_status("错误: 无已启用通道", is_error=True)
                self.is_test_running = False
                self._update_test_button_state(False)
                self._set_ui_enabled(True)
                return
            fn = self._run_multi_ch_temp_test
            kwargs = dict(
                device_addr=iic_device_addr,
                reg_addr=iic_reg_addr,
                iic_weight=iic_width,
                temp_min=self.temp_min.value(),
                temp_max=self.temp_max.value(),
                temp_step=self.temp_step.value(),
                soak_time=self.soak_time.value(),
                sample_cnt=sample_cnt,
                channels=channels,
                pre_config=self.multi_ch_panel.get_pre_config(),
            )
        elif test_item == self.TEST_FT_CALIB_CHECK:
            ft_cfg = self._parse_ft_calib_inputs()
            if ft_cfg is None:
                self.is_test_running = False
                self._update_test_button_state(False)
                self._set_ui_enabled(True)
                return
            fn = self._run_ft_calib_check
            kwargs = dict(
                device_addr=iic_device_addr,
                reg_addr=iic_reg_addr,
                iic_weight=iic_width,
                voltage_min=self.voltage_min.value(),
                voltage_max=self.voltage_max.value(),
                voltage_step=self.voltage_step.value(),
                voltage_channel=self.voltage_channel.currentData(),
                sample_cnt=sample_cnt,
                **ft_cfg,
            )
        else:
            self._stop_test()
            return

        # 测试用到的 N6705C 通道在结束后恢复测试前电压设定（快照/恢复在 worker 线程内执行）
        restore_channels = self._voltage_channels_for_test(test_item, kwargs)
        if restore_channels:
            fn = self._wrap_restore_channel_voltage(fn, restore_channels)

        worker = _TestWorker(fn, kwargs)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_test_done)
        worker.error.connect(self._on_test_error)
        worker.log.connect(self._append_log)
        worker.progress.connect(self.set_progress)
        worker.confirm_request.connect(self._on_worker_confirm_request)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_test_thread_finished)

        self._test_worker = worker
        self.test_thread = thread
        thread.start()

    def _voltage_channels_for_test(self, test_item, kwargs):
        """返回本次测试会改动电压设定的 N6705C 通道列表（去重，保持顺序）。"""
        if test_item in (self.TEST_FORCE_VOLTAGE, self.TEST_TEMP_CONSISTENCY,
                         self.TEST_FT_CALIB_CHECK):
            return [kwargs['voltage_channel']]
        if test_item == self.TEST_MULTI_CH_TEMP:
            channels = []
            for ch_cfg in kwargs['channels']:
                if ch_cfg.get('enabled', True) and ch_cfg.get('sweep_enabled'):
                    vch = int(ch_cfg.get('voltage_channel') or 1)
                    if vch not in channels:
                        channels.append(vch)
            return channels
        return []

    def _wrap_restore_channel_voltage(self, fn, channels):
        """包装测试函数：worker 线程内先 measure_voltage 快照各通道电压，测试结束（含中止/异常）后恢复。"""
        def _runner(stop_check=None, **fn_kwargs):
            saved = {}
            if not DEBUG_MOCK and self.n6705c is not None:
                for ch in channels:
                    try:
                        saved[ch] = self.n6705c.measure_voltage(ch)
                    except Exception:
                        logger.warning("GPADC 读取 CH%s 测试前电压失败", ch, exc_info=True)
            try:
                return fn(stop_check=stop_check, **fn_kwargs)
            finally:
                for ch, voltage in saved.items():
                    try:
                        self.n6705c.set_voltage(ch, voltage)
                        self._test_worker.log.emit(f"[INFO] CH{ch} 电压已恢复测试前设定: {voltage:.3f} V")
                    except Exception:
                        logger.warning("GPADC 恢复 CH%s 电压失败", ch, exc_info=True)
                        self._test_worker.log.emit(f"[WARN] CH{ch} 电压恢复失败，请手动确认通道输出")
        return _runner

    def _run_1000cnt_test(self, device_addr, reg_addr, sample_cnt=1000, iic_weight=10, stop_check=None):
        if self._acq_mode_snapshot == 'UART':
            self._test_worker.log.emit(f"[INFO] Starting 1000CNT TEST via UART Log, keyword='{self._uart_keyword_snapshot}', count={sample_cnt}")
        else:
            self._test_worker.log.emit(f"[INFO] Starting 1000CNT TEST with I2C address: 0x{device_addr:x} Register: 0x{reg_addr:x}, count={sample_cnt}")
        _, _, _, raw_data = self._gpadc_read_by_cnts(
            device_addr=device_addr,
            reg_addr=reg_addr,
            iic_weight=iic_weight,
            get_reg_cnt=sample_cnt,
            return_raw=True,
            stop_check=stop_check,
            progress_callback=lambda v: self._test_worker.progress.emit(v),
        )
        stats = compute_detailed_stats(raw_data)
        stats['raw'] = raw_data
        # 算法前后对比（未启用算法为 None），供完成日志输出算法带来的波动改善
        stats['algo_effect'] = self._last_algo_effect
        # 算法前的原始数据（未启用算法为 None），供完成日志输出原始/处理后数据
        stats['raw_before_algo'] = self._last_raw_before_algo
        return ('1000cnt', stats)

    def _run_force_voltage_test(self, device_addr, reg_addr, voltage_min, voltage_max,
                                voltage_step, voltage_channel, sample_cnt=1000, iic_weight=10,
                                stop_check=None):
        result = self.gpadc_force_voltage_test(
            n6705c=self.n6705c,
            device_addr=device_addr,
            reg_addr=reg_addr,
            iic_weight=iic_weight,
            voltage_min=voltage_min,
            voltage_max=voltage_max,
            voltage_step=voltage_step,
            voltage_channel=voltage_channel,
            sample_cnt=sample_cnt,
            stop_check=stop_check,
            progress_callback=lambda v: self._test_worker.progress.emit(v),
        )
        return ('force_voltage', result)

    def _run_high_low_temp_test(self, device_addr, reg_addr, temp_min, temp_max,
                                temp_step, voltage_channel, sample_cnt=1000,
                                iic_weight=10, stop_check=None, soak_time=180):
        self._test_worker.log.emit("[INFO] RUN TEST_HIGH_LOW_TEMP TEST")
        result = self.gpadc_high_low_temp_test(
            device_addr=device_addr,
            reg_addr=reg_addr,
            iic_weight=iic_weight,
            temp_min=temp_min,
            temp_max=temp_max,
            temp_step=temp_step,
            voltage_channel=voltage_channel,
            soak_time=soak_time,
            sample_cnt=sample_cnt,
            stop_check=stop_check,
            progress_callback=lambda v: self._test_worker.progress.emit(v),
        )
        return ('high_low_temp', result)

    def _run_temp_consistency_test(self, device_addr, reg_addr, temp_min, temp_max,
                                   temp_step, voltage_min, voltage_max, voltage_step,
                                   voltage_channel, sample_cnt=1000, iic_weight=10,
                                   stop_check=None, soak_time=180):
        self._test_worker.log.emit("[INFO] RUN TEST_TEMP_CONSISTENCY TEST")
        result = self.gpadc_temp_consistency_test(
            device_addr=device_addr,
            reg_addr=reg_addr,
            iic_weight=iic_weight,
            temp_min=temp_min,
            temp_max=temp_max,
            temp_step=temp_step,
            voltage_min=voltage_min,
            voltage_max=voltage_max,
            voltage_step=voltage_step,
            voltage_channel=voltage_channel,
            soak_time=soak_time,
            sample_cnt=sample_cnt,
            stop_check=stop_check,
            progress_callback=lambda v: self._test_worker.progress.emit(v),
        )
        return ('temp_consistency', result)

    def _run_multi_ch_temp_test(self, device_addr, reg_addr, iic_weight,
                                temp_min, temp_max, temp_step, soak_time, sample_cnt,
                                channels, pre_config, stop_check=None):
        """多通道高低温联合测试：流程在 core/pmu_test/gpadc/gpadc_multi_temp.py（纯函数）。

        本方法仅做仪器/回调装配：温箱 + N6705C + IIC 写/读 + GPADC 采样回调。
        """
        self._test_worker.log.emit("[INFO] RUN TEST_MULTI_CH_TEMP TEST")

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
            chamber = self.chamber
            need_sweep = any(
                c.get('enabled', True) and c.get('sweep_enabled') for c in channels
            )
            if need_sweep and (self.n6705c is None or not self.is_connected):
                self._test_worker.log.emit("[ERROR] N6705C not connected")
                self.set_system_status("错误: N6705C未连接", is_error=True)
                return None
            vol_source = self.n6705c if need_sweep else None
            if (self._acq_mode_snapshot == 'UART'
                    and any((c.get('switch_writes_text') or c.get('switch_writes'))
                            for c in channels if c.get('enabled', True))):
                self._test_worker.log.emit(
                    "[INFO] UART 采集模式下，通道切换仍经 I2C 接口写入"
                )

        def _write_fn(dev, reg, val, width, high=-1, low=-1):
            if DEBUG_MOCK:
                self._mock_i2c.write(dev, reg, val, width)
                return
            self._ensure_device_i2c().write(dev, reg, val, width, high, low)

        def _read_reg_fn(dev, reg, width):
            if DEBUG_MOCK:
                return self._mock_i2c.read(dev, reg, width)
            return self._ensure_device_i2c().read(dev, reg, width)

        def _sample_fn(ch_cfg, cnt, stop, mock_hint=None):
            dev = parse_hw_int(ch_cfg.get('read_dev'), device_addr)
            reg = parse_hw_int(ch_cfg.get('read_reg'), reg_addr)
            width = int(ch_cfg.get('read_width') or 0) or iic_weight
            if DEBUG_MOCK and mock_hint is not None:
                self._mock_i2c.set_mock_voltage(mock_hint)
            return self._gpadc_read_by_cnts(
                dev, reg, width,
                get_reg_cnt=cnt,
                return_raw=False,
                stop_check=stop,
            )

        result = run_multi_ch_temp_test(
            chamber=chamber,
            vol_source=vol_source,
            write_fn=_write_fn,
            read_reg_fn=_read_reg_fn,
            sample_fn=_sample_fn,
            channels=channels,
            pre_config=pre_config,
            temp_min=temp_min,
            temp_max=temp_max,
            temp_step=temp_step,
            soak_time=soak_time,
            sample_cnt=sample_cnt,
            default_dev=device_addr,
            default_width=iic_weight,
            mock_mode=DEBUG_MOCK,
            log_fn=self._test_worker.log.emit,
            status_fn=lambda msg, is_err=False: self.set_system_status(msg, is_err),
            stop_check=stop_check,
            progress_callback=lambda v: self._test_worker.progress.emit(v),
        )
        return ('multi_ch_temp', result)

    def _run_ft_calib_check(self, device_addr, reg_addr, iic_weight,
                            voltage_min, voltage_max, voltage_step, voltage_channel,
                            calib_p1, calib_p2, raw_tol_lsb, err_limit_mv,
                            divider_ratio=1.0, sample_cnt=1000, stop_check=None):
        """FT Calibration Check：流程纯函数在 core/pmu_test/gpadc/gpadc_ft_check.py。

        本方法仅做仪器/回调装配：N6705C 扫压 + IIC 实时采样 / UART raw/volt 解析。
        """
        mode = self._acq_mode_snapshot
        self._test_worker.log.emit(f"[INFO] RUN FT CALIBRATION CHECK ({mode})")

        if DEBUG_MOCK:
            if not hasattr(self, "_mock_i2c"):
                self._mock_i2c = MockI2C()
            vol_source = MockN6705C()
            vol_source._mock_i2c = self._mock_i2c
        else:
            vol_source = self.n6705c
            if vol_source is None or not self.is_connected:
                self._test_worker.log.emit("[ERROR] N6705C not connected")
                self.set_system_status("错误: N6705C未连接", is_error=True)
                return None

        # FT 校准检查不应用采样算法与离群筛选（保持 raw 与 volt 的配对一致性）
        if self._algorithm_snapshot is not None:
            self._test_worker.log.emit("[INFO] FT Calibration Check 不应用采样算法，已忽略 Algorithm 配置")
        saved_algo = self._algorithm_snapshot
        self._algorithm_snapshot = None
        if self._outlier_filter_snapshot is not None:
            self._test_worker.log.emit("[INFO] FT Calibration Check 不应用离群样本筛选，已忽略 Outlier Filter 配置")
        saved_filter = self._outlier_filter_snapshot
        self._outlier_filter_snapshot = None
        try:
            def _set_voltage(v):
                vol_source.set_voltage(voltage_channel, v)
                if DEBUG_MOCK:
                    # 模拟外部分压：MockN6705C 默认把 DUT 输入设为源输出，
                    # 实际分压场景 DUT 引脚电压 = 源输出 / 分压比
                    self._mock_i2c.set_mock_voltage(v / divider_ratio)

            def _sample_iic(cnt, stop):
                return self.gpadc_reg_read_by_cnts(
                    device_addr, reg_addr, iic_weight,
                    get_reg_cnt=cnt, return_raw=False, stop_check=stop,
                )

            def _sample_uart(cnt, stop):
                return self.gpadc_uart_read_raw_volt_by_cnts(
                    get_reg_cnt=cnt,
                    keyword=self._uart_keyword_snapshot,
                    stop_check=stop,
                )

            result = run_ft_calib_check(
                mode=mode,
                calib_p1=calib_p1,
                calib_p2=calib_p2,
                raw_tol_lsb=raw_tol_lsb,
                err_limit_mv=err_limit_mv,
                divider_ratio=divider_ratio,
                voltage_min=voltage_min,
                voltage_max=voltage_max,
                voltage_step=voltage_step,
                sample_cnt=sample_cnt,
                set_voltage_fn=_set_voltage,
                sample_iic_fn=_sample_iic,
                sample_uart_fn=_sample_uart,
                settle_s=0.0 if DEBUG_MOCK else 0.5,
                step_s=0.0 if DEBUG_MOCK else 0.2,
                log_fn=self._test_worker.log.emit,
                status_fn=lambda msg, is_err=False: self.set_system_status(msg, is_err),
                stop_check=stop_check,
                progress_callback=lambda v: self._test_worker.progress.emit(v),
            )
        finally:
            self._algorithm_snapshot = saved_algo
            self._outlier_filter_snapshot = saved_filter
        if result is None:
            return None
        return ('ft_calib_check', result)

    def _on_test_done(self, payload):
        if payload is None:
            return
        kind, result = payload

        if kind == '1000cnt':
            self.update_test_result(result)
            self._append_log(
                f"[RESULT] 1000CNT TEST: AVG={result.get('avg', 0):.3f}, MIN={result.get('min', 0):.3f}, "
                f"MAX={result.get('max', 0):.3f}, STD={result.get('std', 0):.3f}, "
                f"P-P={result.get('pp', 0):.0f} code, N={result.get('count', 0)}"
            )
            # 原始数据波动评估（STD 分级，阈值为 gpadc_analysis 的 FLUCT_STD_* 常量）
            self._append_log(
                f"[RESULT] 波动评估: "
                f"{assess_fluctuation(result.get('std', 0), result.get('pp', 0))}"
            )
            # 算法带来的波动改善（启用算法时输出前后对比）
            effect = result.get('algo_effect')
            if effect:
                std_pct = ('n/a' if effect['std_improve_pct'] is None
                           else f"{effect['std_improve_pct']:+.1f}%")
                pp_pct = ('n/a' if effect['pp_improve_pct'] is None
                          else f"{effect['pp_improve_pct']:+.1f}%")
                self._append_log(
                    f"[ALGO] {describe_algorithm(self._algorithm_snapshot)} 波动改善: "
                    f"STD {effect['std_before']:.3f}→{effect['std_after']:.3f} code ({std_pct}), "
                    f"P-P {effect['pp_before']:.0f}→{effect['pp_after']:.0f} code ({pp_pct}), "
                    f"N {effect['count_before']}→{effect['count_after']}"
                )
            # 输出原始数据与处理后数据（未启用算法时二者一致，仅输出 RAW 一次）
            raw_before = result.get('raw_before_algo')
            if raw_before is not None:
                self._log_data_series("RAW (原始数据)", raw_before)
                self._log_data_series(
                    f"PROC (处理后, {describe_algorithm(self._algorithm_snapshot)})",
                    result.get('raw'),
                )
            else:
                self._log_data_series("RAW (原始数据)", result.get('raw'))
            self._plot_cnt_distribution(result, self._algorithm_snapshot)

        elif kind == 'force_voltage':
            if result is not None:
                # 新测试完成：默认显示单次全部波形（Voltage / Min-Max / Error）
                self._set_curve_view_all(True)
                result_after_calibration = self._calibration_data(result)
                voltage_data, mean_cali, adc_min_cali, adc_max_cali = result_after_calibration
                params = self._calculate_gpadc_parameters(result)
                # 逐点悬浮预览数据（RAW=算法前，PROC=处理后）
                self._fv_hover_data = {
                    'mode': 'fv',
                    'x': list(voltage_data),
                    'y': list(mean_cali),
                    'raw_samples': result.get('raw_samples') or [],
                    'raw_before': result.get('raw_before_samples') or [],
                    'algorithm': self._algorithm_snapshot,
                }
                self._plot_voltage_adc_curve(voltage_data, mean_cali, adc_min_cali, adc_max_cali)
                self.update_test_result(params)
                self._export_data = {
                    'params': params,
                    'raw': result,
                    'calibration': {
                        'voltage': voltage_data,
                        'mean_cali': mean_cali,
                        'min_cali': adc_min_cali,
                        'max_cali': adc_max_cali,
                    }
                }

        elif kind == 'high_low_temp':
            if result is not None:
                # 新测试完成：默认显示单次全部波形（Voltage / Min-Max / Error）
                self._set_curve_view_all(True)
                temp_data, mean_cali, adc_min_cali, adc_max_cali = self._calibration_data(result)
                params = self._calculate_gpadc_parameters(result)
                self._plot_voltage_adc_curve(temp_data, mean_cali, adc_min_cali, adc_max_cali, is_temp_mode=True)
                self.update_test_result(params)
                self._export_data = {
                    'params': params,
                    'raw': result,
                    'calibration': {
                        'voltage': temp_data,
                        'mean_cali': mean_cali,
                        'min_cali': adc_min_cali,
                        'max_cali': adc_max_cali,
                    }
                }
                self.set_system_status("GPADC温度测试完成")

        elif kind == 'temp_consistency':
            if result is not None:
                # 新测试完成：默认显示单次全部波形（Mean / Min-Max）
                self._set_curve_view_all(True)
                self._plot_temp_consistency_curves(result)
                self._export_data = {'raw': result}
                self._append_log("[RESULT] Temp Consistency Test completed")
                self.set_system_status("GPADC温度一致性测试完成")

        elif kind == 'multi_ch_temp':
            if result is not None:
                self._set_curve_view_all(True)
                # 扫压通道逐温度行做两点标定（与 temp_consistency 同语义），结果附回 channel dict
                self._compute_multi_ch_calibration(result)
                self._plot_multi_ch_temp_curves(result)
                self._export_data = {'multi_ch_temp': result}
                self._append_log("[RESULT] Multi-Ch Temp Test completed")
                self.set_system_status("GPADC多通道温度测试完成")

        elif kind == 'ft_calib_check':
            if result is not None:
                stats = result.get('stats') or {}
                passed = result.get('passed', False)
                self._update_ft_result_cards(result)
                self._plot_ft_check_curve(result)
                self._append_log(
                    f"[RESULT] FT Calibration Check 判定: {'PASS' if passed else 'FAIL'} "
                    f"(MaxErr={stats.get('max_abs_mv', 0):.2f} mV, "
                    f"限 ±{result.get('err_limit_mv', 0):.1f} mV)"
                )
                self._export_data = {
                    'params': {
                        'max_err_mv': stats.get('max_abs_mv'),
                        'avg_err_mv': stats.get('avg_mv'),
                        'rms_err_mv': stats.get('rms_mv'),
                        'passed': passed,
                    },
                    'ft_calib': result,
                }
                self.set_system_status(
                    f"FT校准检查{'通过' if passed else '未通过'}", is_error=not passed)

        # 记入最近测试列表，供后续对比/载入
        self._record_recent_test(kind, result)
        # 曲线类测试完成后，当前图上显示的就是这条记录（右键切换 Curve View 时据此重绘）
        if self._recent_test_records and self._recent_test_records[-1]['kind'] in self._CURVE_KINDS:
            self._loaded_record = self._recent_test_records[-1]

    def _on_test_error(self, err):
        self._append_log(f"[ERROR] Test error: {err}")

    def _on_worker_confirm_request(self, title: str, message: str):
        """Worker 确认请求（温箱通信失败等可恢复错误）→ 弹窗让用户决定重试/中止。

        Worker 阻塞等待应答；选“重试”重测当前温度点，选“中止”或按 Esc 结束测试。
        """
        box = QMessageBox(self)
        box.setWindowTitle(title)
        box.setIcon(QMessageBox.Warning)
        box.setText(message)
        retry_btn = box.addButton("重试", QMessageBox.YesRole)
        abort_btn = box.addButton("中止", QMessageBox.NoRole)
        box.setDefaultButton(abort_btn)
        box.setEscapeButton(abort_btn)
        apply_qss(box, "dialog")
        box.exec()
        if self._test_worker is not None:
            try:
                self._test_worker.respond_confirm(box.clickedButton() is retry_btn)
            except RuntimeError:
                # 弹窗期间用户按 Stop，worker 已随线程销毁
                pass

    def _on_test_thread_finished(self):
        self._test_worker = None
        if self.test_thread is not None:
            self.test_thread.deleteLater()
            self.test_thread = None
        self.is_test_running = False
        self.start_test_btn.setEnabled(True)
        self.stop_test_btn.setEnabled(False)
        self._update_test_button_state(False)
        self._set_ui_enabled(True)
        # 通知 AI 异步动作层：测试结束，触发 pending 任务回灌续跑（§4 / S3-2）。
        stopped = bool(getattr(self, "_test_stop_requested", False))
        summary = "测试被中止" if stopped else "测试完成"
        self.sequence_execution_finished.emit(not stopped, summary)

    def _update_test_button_state(self, running):
        update_start_btn_state(self.start_test_btn, running,
                               start_text=self._start_btn_text,
                               stop_text="■ STOP")

    def _stop_test(self):
        if self._test_worker is not None:
            self._test_worker.request_stop()
        self._test_stop_requested = True
        if self.test_thread is not None and self.test_thread.isRunning():
            self.test_thread.quit()
        # 禁在 UI 线程 wait()：worker 收尾耗时不可控（UART 采集等待、仪器超时等），
        # 无限期阻塞会卡死窗口；线程收尾由 thread.finished → _on_test_thread_finished 异步复位。
        self._append_log("[INFO] Stopping GPADC test...")

    def cleanup_threads(self):
        try:
            from shiboken6 import isValid
        except ImportError:
            isValid = lambda obj: obj is not None

        for attr in ('_n6705c_search_thread', '_chamber_search_thread', '_serial_search_thread'):
            thread = getattr(self, attr, None)
            if thread is not None and isValid(thread) and thread.isRunning():
                thread.quit()
                thread.wait(3000)
            setattr(self, attr, None)

        if self._test_worker is not None:
            self._test_worker.request_stop()
        if self.test_thread is not None and isValid(self.test_thread) and self.test_thread.isRunning():
            self.test_thread.quit()
            self.test_thread.wait(3000)
        self.test_thread = None
