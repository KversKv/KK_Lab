#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force 测试 Worker 基类以及两个具体实现:
  - ForceHigh:基于默认电压 +20mV 加压测试
  - ForceAuto:基于 prepare_force_auto 自动电压对齐测试

两者 90% 的流程相同,差异仅在于:
  1. prepare 阶段调用的下位机方法/参数;
  2. 部分日志文案与 channel_result 的 phase 字段。
因此把流程抽象到 BaseForceTestWorker 里,子类只需实现 _do_prepare。
"""

import threading
import time as _time

from PySide6.QtCore import QObject, Signal

from log_config import get_logger

from .common import (
    _format_current_unified,
    build_datalog_tasks,
    build_summary_payload,
    configure_datalog_all,
    fetch_datalog_all,
    format_current_short,
    restore_force_channels,
    run_threads_parallel,
    start_datalog_sync,
    wait_datalog_with_progress,
)

logger = get_logger(__name__)


class BaseForceTestWorker(QObject):
    log_message = Signal(str)
    channel_result = Signal(str, int, float, str)
    test_summary = Signal(dict)
    progress = Signal(float)
    finished = Signal()
    error = Signal(str)

    # 子类覆盖
    _TEST_NAME = "Force"
    _PHASE_TAG = "force"
    _PREPARE_LABEL = "Force auto"

    def __init__(self, vbat_device_label, vbat_inst, vbat_hw_ch,
                 device_map, test_time, sample_period,
                 channel_names=None, force_voltages=None):
        super().__init__()
        self.vbat_device_label = vbat_device_label
        self.vbat_inst = vbat_inst
        self.vbat_hw_ch = vbat_hw_ch
        self.device_map = device_map
        self.test_time = test_time
        self.sample_period = sample_period
        self.channel_names = channel_names or {}
        self.force_voltages = force_voltages or {}
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            self._run_flow()
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    @staticmethod
    def _estimate_datalog_time(test_time):
        return test_time + 4.0

    @staticmethod
    def _estimate_force_time(test_time):
        return test_time + 5.0

    def _make_sub_progress(self, base, span, total_est):
        def _on_progress(frac):
            self.progress.emit(min((base + frac * span) / total_est, 1.0))
        return _on_progress

    # ---- 子类需实现 ----
    def _do_prepare(self, task, forced_chs, normal_chs):
        """在单个仪器上完成 Force 前置设置,返回 measured_voltages 字典。"""
        raise NotImplementedError

    # ---- 主流程 ----
    def _run_flow(self):
        vbat_ch = self.vbat_hw_ch
        vbat_inst = self.vbat_inst
        vbat_label = self.vbat_device_label

        setup_time = 1.0
        step1_time = self._estimate_datalog_time(self.test_time)
        step2_time = self._estimate_force_time(self.test_time)
        total_est = max(setup_time + step1_time + step2_time, 1.0)

        cursor = 0.0
        self.progress.emit(0.0)
        stop_check = lambda: self._is_stopped

        results = {}
        vbat_remain = None
        channel_voltages = {}

        # Step 1: 把所有 sub-channel 复位成 VMETer
        self.log_message.emit("[TEST] Resetting sub-channels to VMeter mode...")
        for device_label, (n6705c_inst, hw_channels) in self.device_map.items():
            for ch in hw_channels:
                try:
                    n6705c_inst.set_mode(ch, "VMETer")
                    n6705c_inst.channel_on(ch)
                except Exception as e:
                    self.log_message.emit(
                        f"[WARNING] Failed to set {device_label}-CH{ch} to VMeter: {e}"
                    )
        cursor = setup_time
        self.progress.emit(cursor / total_est)

        # Step 2: 先在 Vbat 上测总电流
        self.log_message.emit(f"[TEST] Measuring Vbat (CH{vbat_ch}) total current...")
        vbat_result = vbat_inst.fetch_current_by_datalog(
            [vbat_ch], self.test_time, self.sample_period,
            on_progress=self._make_sub_progress(cursor, step1_time, total_est),
            stop_check=stop_check,
        )
        cursor += step1_time
        self.progress.emit(min(cursor / total_est, 1.0))
        if self._is_stopped:
            return

        vbat_current = vbat_result.get(vbat_ch, 0.0)
        logger.debug("%s: Vbat total current = %.6e A", self._TEST_NAME, vbat_current)
        self.channel_result.emit(vbat_label, vbat_ch, float(vbat_current), "vbat")
        results[(vbat_label, vbat_ch)] = float(vbat_current)

        try:
            vbat_v = float(vbat_inst.measure_voltage(vbat_ch))
            channel_voltages[(vbat_label, vbat_ch)] = vbat_v
        except Exception:
            channel_voltages[(vbat_label, vbat_ch)] = 0.0

        # Step 3: 准备并启动 Force
        self.log_message.emit(
            f"[TEST] {self._PREPARE_LABEL} on sub-channels — parallel sync..."
        )
        task_list = build_datalog_tasks(
            self.device_map, vbat_label, vbat_ch, self.sample_period
        )
        if not task_list:
            self.progress.emit(1.0)
            self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
            return

        self.log_message.emit(
            f"[TEST] Preparing {self._PREPARE_LABEL.lower()} on all instruments..."
        )

        def _prepare_worker(idx, task):
            forced_chs, normal_chs = [], []
            for ch in task["force_channels"]:
                fv = self.force_voltages.get((task["device_label"], ch))
                if fv is not None:
                    forced_chs.append((ch, fv))
                else:
                    normal_chs.append(ch)
            task["measured_voltages"] = self._do_prepare(task, forced_chs, normal_chs)

        prepare_errors = run_threads_parallel(task_list, _prepare_worker, timeout=30)
        for idx, err in enumerate(prepare_errors):
            if err:
                dl = task_list[idx]["device_label"]
                self.log_message.emit(
                    f"[ERROR] Prepare {self._PREPARE_LABEL.lower()} failed on {dl}: {err}"
                )

        active_tasks = [t for i, t in enumerate(task_list) if prepare_errors[i] is None]
        for task in active_tasks:
            for ch, v in (task.get("measured_voltages") or {}).items():
                channel_voltages[(task["device_label"], ch)] = v

        if not active_tasks:
            self.progress.emit(1.0)
            self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
            return

        # Step 4: 配置 + 同步启动 datalog
        self.log_message.emit("[TEST] Configuring datalog on all instruments...")
        active_tasks = configure_datalog_all(
            active_tasks, self.test_time, self.log_message.emit
        )
        if not active_tasks:
            self.progress.emit(1.0)
            self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
            return

        self.log_message.emit(
            f"[TEST] Sync-starting datalog on {len(active_tasks)} instrument(s)..."
        )
        logger.debug(
            "%s: sync-starting datalog on %d instruments",
            self._TEST_NAME, len(active_tasks),
        )
        start_datalog_sync(active_tasks, self.log_message.emit, timeout=30)

        # Step 5: 等待采集完成
        total_wait_est = (self.test_time + 1) + 3.0
        wait_progress_span = (self.test_time + 1) / total_wait_est * step2_time

        def _tick(frac):
            self.progress.emit(
                min((cursor + frac * wait_progress_span) / total_est, 1.0)
            )

        if not wait_datalog_with_progress(self.test_time, lambda: self._is_stopped, _tick):
            return

        # Step 6: 并发 fetch 结果
        self.log_message.emit("[TEST] Fetching results from all instruments...")
        fetch_errors = fetch_datalog_all(
            active_tasks, self.test_time, self.log_message.emit, timeout=30
        )
        restore_force_channels(active_tasks)

        cursor = setup_time + step1_time + step2_time
        self.progress.emit(min(cursor / total_est, 1.0))

        for idx, task in enumerate(active_tasks):
            if fetch_errors[idx]:
                continue
            cr = task["curr_result"] or {}
            for ch in task["force_channels"]:
                avg_i = cr.get(ch, 0.0)
                logger.debug(
                    "%s result: %s CH%s = %.6e A",
                    self._TEST_NAME, task["device_label"], ch, avg_i,
                )
                self.channel_result.emit(
                    task["device_label"], ch, float(avg_i), self._PHASE_TAG
                )
                results[(task["device_label"], ch)] = float(avg_i)
            if task["device_label"] == vbat_label and vbat_ch in cr:
                vbat_remain = float(cr[vbat_ch])

        self.progress.emit(1.0)
        self._emit_summary(results, vbat_current, vbat_remain, channel_voltages)
        self.log_message.emit(f"[TEST] {self._TEST_NAME} consumption test completed.")

    def _emit_summary(self, results, vbat_current, vbat_remain, channel_voltages=None):
        summary, _ = build_summary_payload(
            device_map=self.device_map,
            channel_names=self.channel_names,
            vbat_label=self.vbat_device_label,
            vbat_ch=self.vbat_hw_ch,
            results=results,
            vbat_current=vbat_current,
            vbat_remain=vbat_remain,
            channel_voltages=channel_voltages,
            log_fn=self.log_message.emit,
        )
        self.test_summary.emit(summary)

    # 兼容 ConsumptionTestUI 以前直接访问
    _format_current_short = staticmethod(format_current_short)


class ConsumptionTestForceHighWorker(BaseForceTestWorker):
    """Force high:默认电压 +20mV。"""

    _TEST_NAME = "ForceHigh"
    _PHASE_TAG = "force_high"
    _PREPARE_LABEL = "Force high (+20mV)"

    def __init__(self, vbat_device_label, vbat_inst, vbat_hw_ch,
                 force_high_map, test_time, sample_period,
                 channel_names=None, force_voltages=None):
        super().__init__(
            vbat_device_label, vbat_inst, vbat_hw_ch,
            force_high_map, test_time, sample_period,
            channel_names=channel_names, force_voltages=force_voltages,
        )

    # 向后兼容的属性别名
    @property
    def force_high_map(self):
        return self.device_map

    def _do_prepare(self, task, forced_chs, normal_chs):
        mv = {}
        if normal_chs:
            mv = task["inst"].prepare_force_high(
                normal_chs,
                voltage_offset=0.02,
                current_limit=0.05,
                monitor_channels=task["monitor_channels"],
            )
        for ch, fv in forced_chs:
            ch_name = self.channel_names.get(
                (task["device_label"], ch), f"{task['device_label']}-CH{ch}"
            )
            self.log_message.emit(
                f"[TEST] Force Vol: {ch_name} -> {fv:.4f}V (user override)"
            )
            task["inst"].set_mode(ch, "PS2Q")
            task["inst"].set_voltage(ch, fv)
            task["inst"].set_current_limit(ch, 1.0)
            task["inst"].channel_on(ch)
            mv[ch] = fv
        if forced_chs:
            _time.sleep(0.5)
        return mv


class ConsumptionTestForceWorker(BaseForceTestWorker):
    """Force auto:基于 prepare_force_auto。"""

    _TEST_NAME = "ForceAuto"
    _PHASE_TAG = "force_auto"
    _PREPARE_LABEL = "Force auto (align voltage)"

    def __init__(self, vbat_device_label, vbat_inst, vbat_hw_ch,
                 force_map, test_time, sample_period,
                 channel_names=None, force_voltages=None):
        super().__init__(
            vbat_device_label, vbat_inst, vbat_hw_ch,
            force_map, test_time, sample_period,
            channel_names=channel_names, force_voltages=force_voltages,
        )

    @property
    def force_map(self):
        return self.device_map

    def _do_prepare(self, task, forced_chs, normal_chs):
        mv = {}
        if normal_chs:
            mv = task["inst"].prepare_force_auto(
                normal_chs,
                current_limit=0.05,
                monitor_channels=task["monitor_channels"],
            )
        for ch, fv in forced_chs:
            ch_name = self.channel_names.get(
                (task["device_label"], ch), f"{task['device_label']}-CH{ch}"
            )
            self.log_message.emit(
                f"[TEST] Force Vol: {ch_name} -> {fv:.4f}V (user override)"
            )
            task["inst"].set_mode(ch, "PS2Q")
            task["inst"].set_voltage(ch, fv)
            task["inst"].set_current_limit(ch, 1.0)
            task["inst"].channel_on(ch)
            final_limit = 0.07 if fv < 1.0 else 0.15
            task["inst"].set_current_limit(ch, final_limit)
            mv[ch] = fv
        if forced_chs:
            _time.sleep(0.5)
        return mv


__all__ = [
    "BaseForceTestWorker",
    "ConsumptionTestForceHighWorker",
    "ConsumptionTestForceWorker",
]
