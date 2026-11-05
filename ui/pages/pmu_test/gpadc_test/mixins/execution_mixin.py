"""GPADCTestUI 测试启停 / 编排 / Worker 生命周期 Mixin。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来。
类装配见 gpadc_test_ui.py。"""

import weakref

from ui.styles import update_start_btn_state
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QThread
from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockChamber, MockN6705C
from ui.theme import apply_qss
from core.pmu_test.gpadc import (
    TestWorker as _TestWorker, GPADCTestRunner,
    ALGORITHM_REGISTRY, describe_algorithm, assess_fluctuation, freeze_config,
)

_RETIRED_THREAD_WORKERS = {}


class _WorkerSignalRelay:
    """只弱引用 Worker，不捕获页面或 Widget 的 core 回调中继。"""

    def __init__(self, worker=None):
        self._worker_ref = weakref.ref(worker) if worker is not None else None

    def attach(self, worker):
        self._worker_ref = weakref.ref(worker)

    def _worker(self):
        return self._worker_ref() if self._worker_ref is not None else None

    def log(self, message):
        worker = self._worker()
        if worker is not None:
            worker.log.emit(message)

    def status(self, message, is_error=False):
        worker = self._worker()
        if worker is not None:
            worker.status.emit(message, is_error)

    def progress(self, value):
        worker = self._worker()
        if worker is not None:
            worker.progress.emit(value)

    def confirm(self, title, message):
        worker = self._worker()
        if worker is None:
            return False, False
        return worker.wait_user_confirm(title, message)


def _retire_thread(thread, worker=None):
    """脱离页面父级并保留引用，线程结束后由事件循环异步回收。"""
    _RETIRED_THREAD_WORKERS[thread] = worker
    thread.setParent(None)
    thread.finished.connect(thread.deleteLater)
    thread.finished.connect(lambda: _RETIRED_THREAD_WORKERS.pop(thread, None))
    thread.quit()
    if not thread.isRunning():
        _RETIRED_THREAD_WORKERS.pop(thread, None)
        thread.deleteLater()


class _ExecutionMixin:
    """测试启停 / 编排 / Worker 生命周期 Mixin"""

    def _on_start_or_stop(self):
        if self.is_test_running:
            self._stop_test()
        else:
            self._start_test()

    def _validate_test_ranges(self, test_item):
        if (test_item in (self.TEST_FORCE_VOLTAGE, self.TEST_TEMP_CONSISTENCY,
                          self.TEST_FT_CALIB_CHECK)
                and self.voltage_min.value() > self.voltage_max.value()):
            return "电压扫描范围无效：Start <= End 必须成立"
        if (test_item in (self.TEST_HIGH_LOW_TEMP, self.TEST_TEMP_CONSISTENCY,
                          self.TEST_MULTI_CH_TEMP)
                and self.temp_min.value() > self.temp_max.value()):
            return "温度扫描范围无效：Start <= End 必须成立"
        if test_item == self.TEST_MULTI_CH_TEMP:
            for channel in self.multi_ch_panel.get_channels():
                if (channel.get('enabled', True) and channel.get('sweep_enabled')
                        and channel.get('v_min', 0.0) > channel.get('v_max', 0.0)):
                    name = channel.get('name') or "未命名通道"
                    return f"通道 {name} 电压扫描范围无效：Start <= End 必须成立"
        return None

    def _start_test(self):
        if self.is_test_running:
            return

        test_item = self.current_test_item
        range_error = self._validate_test_ranges(test_item)
        if range_error is not None:
            self._append_log(f"[ERROR] {range_error}")
            self.set_system_status(f"错误: {range_error}", is_error=True)
            return

        self._acq_mode_snapshot = 'UART' if self.uart_radio.isChecked() else 'IIC'
        self._uart_keyword_snapshot = self.uart_keyword.text().strip()
        self._calib_points_snapshot = self._parse_calib_points()
        if self._calib_points_snapshot is not None:
            v_lo, v_hi = self._calib_points_snapshot
            self._append_log(f"[INFO] 使用手动校准点: low={v_lo}, high={v_hi}")
        self._algorithm_snapshot = freeze_config(self._collect_algorithm_config())
        if self._algorithm_snapshot is not None:
            self._append_log(f"[INFO] 启用采样算法: {describe_algorithm(self._algorithm_snapshot)}")
            _algo_spec = ALGORITHM_REGISTRY.get(self._algorithm_snapshot['id']) or {}
            if _algo_spec.get('principle'):
                self._append_log(f"[INFO] {_algo_spec['principle']}")
        self._iic_speed_snapshot = I2CSpeedMode(self.iic_speed_combo.currentData())
        if self.outlier_filter_switch.isChecked():
            self._outlier_filter_snapshot = freeze_config({
                'pos': self.outlier_pos_offset.value(),
                'neg': self.outlier_neg_offset.value(),
            })
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

        iic_device_addr = int(self.iic_device_address.text(), 16)
        iic_reg_addr = int(self.iic_data_address.text(), 16)
        iic_width = self.iic_width_combo.currentData()
        sample_cnt = self.sample_count.value()

        if test_item == self.TEST_1000CNT:
            kind = "1000cnt"
            kwargs = dict(
                device_addr=iic_device_addr,
                reg_addr=iic_reg_addr,
                iic_weight=iic_width,
                sample_cnt=sample_cnt,
            )
        elif test_item == self.TEST_FORCE_VOLTAGE:
            kind = "force_voltage"
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
            kind = "high_low_temp"
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
            kind = "temp_consistency"
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
            kind = "multi_ch_temp"
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
            kind = "ft_calib_check"
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

        relay = _WorkerSignalRelay()
        runner = self._build_gpadc_runner(relay)
        worker = _TestWorker(runner.run, {"kind": kind, "config": kwargs})
        relay.attach(worker)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_test_done)
        worker.error.connect(self._on_test_error)
        worker.log.connect(self._append_log)
        worker.status.connect(self.set_system_status)
        worker.progress.connect(self.set_progress)
        worker.confirm_request.connect(self._on_worker_confirm_request)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_test_thread_finished)

        self._test_worker = worker
        self._test_runner = runner
        self.test_thread = thread
        thread.start()

    def _build_gpadc_runner(self, relay):
        """装配纯 core runner；仪器与采集对象均不反向引用页面。"""
        acquisition = self._create_gpadc_acquisition(
            log_fn=relay.log,
            status_fn=relay.status,
        )
        if DEBUG_MOCK:
            n6705c = MockN6705C()
            n6705c._mock_i2c = acquisition.mock_i2c
            chamber = MockChamber()
        else:
            n6705c = getattr(self, "n6705c", None)
            chamber = getattr(self, "chamber", None)
        return GPADCTestRunner(
            acquisition=acquisition,
            n6705c=n6705c,
            chamber=chamber,
            n6705c_connected=DEBUG_MOCK or bool(getattr(self, "is_connected", False)),
            chamber_connected=DEBUG_MOCK or bool(getattr(self, "is_chamber_connected", False)),
            mock_mode=DEBUG_MOCK,
            calib_points=self._calib_points_snapshot,
            log_fn=relay.log,
            status_fn=relay.status,
            progress_callback=relay.progress,
            confirm_fn=relay.confirm,
        )

    def _run_gpadc_compat(self, kind, config, stop_check=None):
        """旧页内入口的兼容转发；正常启动路径直接绑定 core runner。"""
        relay = _WorkerSignalRelay(getattr(self, "_test_worker", None))
        runner = self._build_gpadc_runner(relay)
        return runner.run(kind, config, stop_check=stop_check)

    def _run_1000cnt_test(self, device_addr, reg_addr, sample_cnt=1000, iic_weight=10, stop_check=None):
        return self._run_gpadc_compat("1000cnt", dict(
            device_addr=device_addr, reg_addr=reg_addr, iic_weight=iic_weight,
            sample_cnt=sample_cnt,
        ), stop_check)

    def _run_force_voltage_test(self, device_addr, reg_addr, voltage_min, voltage_max,
                                voltage_step, voltage_channel, sample_cnt=1000, iic_weight=10,
                                stop_check=None):
        return self._run_gpadc_compat("force_voltage", dict(
            device_addr=device_addr, reg_addr=reg_addr, iic_weight=iic_weight,
            voltage_min=voltage_min, voltage_max=voltage_max, voltage_step=voltage_step,
            voltage_channel=voltage_channel, sample_cnt=sample_cnt,
        ), stop_check)

    def _run_high_low_temp_test(self, device_addr, reg_addr, temp_min, temp_max,
                                temp_step, voltage_channel, sample_cnt=1000,
                                iic_weight=10, stop_check=None, soak_time=180):
        return self._run_gpadc_compat("high_low_temp", dict(
            device_addr=device_addr, reg_addr=reg_addr, iic_weight=iic_weight,
            temp_min=temp_min, temp_max=temp_max, temp_step=temp_step,
            voltage_channel=voltage_channel, soak_time=soak_time, sample_cnt=sample_cnt,
        ), stop_check)

    def _run_temp_consistency_test(self, device_addr, reg_addr, temp_min, temp_max,
                                   temp_step, voltage_min, voltage_max, voltage_step,
                                   voltage_channel, sample_cnt=1000, iic_weight=10,
                                   stop_check=None, soak_time=180):
        return self._run_gpadc_compat("temp_consistency", dict(
            device_addr=device_addr, reg_addr=reg_addr, iic_weight=iic_weight,
            temp_min=temp_min, temp_max=temp_max, temp_step=temp_step,
            voltage_min=voltage_min, voltage_max=voltage_max, voltage_step=voltage_step,
            voltage_channel=voltage_channel, soak_time=soak_time, sample_cnt=sample_cnt,
        ), stop_check)

    def _run_multi_ch_temp_test(self, device_addr, reg_addr, iic_weight,
                                temp_min, temp_max, temp_step, soak_time, sample_cnt,
                                channels, pre_config, stop_check=None):
        return self._run_gpadc_compat("multi_ch_temp", dict(
            device_addr=device_addr, reg_addr=reg_addr, iic_weight=iic_weight,
            temp_min=temp_min, temp_max=temp_max, temp_step=temp_step,
            soak_time=soak_time, sample_cnt=sample_cnt,
            channels=channels, pre_config=pre_config,
        ), stop_check)

    def _run_ft_calib_check(self, device_addr, reg_addr, iic_weight,
                            voltage_min, voltage_max, voltage_step, voltage_channel,
                            calib_p1, calib_p2, raw_tol_lsb, err_limit_mv,
                            divider_ratio=1.0, sample_cnt=1000, stop_check=None):
        return self._run_gpadc_compat("ft_calib_check", dict(
            device_addr=device_addr, reg_addr=reg_addr, iic_weight=iic_weight,
            voltage_min=voltage_min, voltage_max=voltage_max, voltage_step=voltage_step,
            voltage_channel=voltage_channel, sample_cnt=sample_cnt,
            calib_p1=calib_p1, calib_p2=calib_p2,
            raw_tol_lsb=raw_tol_lsb, err_limit_mv=err_limit_mv,
            divider_ratio=divider_ratio,
        ), stop_check)

    @staticmethod
    def _result_has_samples(kind, result):
        if kind in ('force_voltage', 'high_low_temp'):
            return bool(result.get('voltage')) and bool(result.get('mean'))
        if kind == 'temp_consistency':
            return bool(result.get('temp')) and any(result.get('mean') or [])
        if kind == 'multi_ch_temp':
            if not result.get('temp'):
                return False
            for channel in result.get('channels') or []:
                rows = channel.get('mean') or []
                if (any(rows) if channel.get('sweep') else bool(rows)):
                    return True
            return False
        return True

    def _on_test_done(self, payload):
        if payload is None:
            return
        kind, result = payload

        empty_result_labels = {
            'force_voltage': "GPADC电压扫描",
            'high_low_temp': "GPADC高低温测试",
            'temp_consistency': "GPADC温度一致性测试",
            'multi_ch_temp': "GPADC多通道温度测试",
        }
        if (result is not None and kind in empty_result_labels
                and not self._result_has_samples(kind, result)):
            label = empty_result_labels[kind]
            self._append_log(f"[WARN] {label}未采集到有效数据，跳过标定、绘图与记录")
            self.set_system_status(f"{label}未采集到有效数据", is_error=True)
            return

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
        self._test_runner = None
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
            worker = getattr(self, attr.replace('_thread', '_worker'), None)
            if thread is not None and isValid(thread):
                _retire_thread(thread, worker if worker is None or isValid(worker) else None)
            setattr(self, attr, None)
            setattr(self, attr.replace('_thread', '_worker'), None)

        worker = self._test_worker
        if worker is not None and isValid(worker):
            worker.request_stop()
            worker.respond_confirm(False)
        thread = self.test_thread
        if thread is not None and isValid(thread):
            _retire_thread(thread, worker if worker is None or isValid(worker) else None)
        # 置空可避免 CleanupMixin 再次在主线程 wait；worker 引用保留到 run 返回。
        self._test_runner = None
        self.test_thread = None
