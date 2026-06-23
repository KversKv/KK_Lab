#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test 公共工具与共享常量。

集中放置跨 Worker 复用的:
 - 单位 / 电流格式化
 - datalog 任务构建、并发启动、并发 fetch 等流程片段
 - emit_summary 辅助
"""

import threading
import time as _time

CURRENT_UNIT = "uA"

_UNIT_CONFIG = {
    "A":  {"scale": 1.0, "suffix": "A"},
    "mA": {"scale": 1e3, "suffix": "mA"},
    "uA": {"scale": 1e6, "suffix": "uA"},
}


def _format_current_unified(current_A, unit=None):
    if unit is None:
        unit = CURRENT_UNIT
    cfg = _UNIT_CONFIG.get(unit, _UNIT_CONFIG["uA"])
    return f"{current_A * cfg['scale']:.4f}{cfg['suffix']}"


def format_current_short(current_A):
    abs_i = abs(current_A)
    if abs_i >= 1:
        return f"{current_A:.4f}A"
    elif abs_i >= 1e-3:
        return f"{current_A*1e3:.4f}mA"
    elif abs_i >= 1e-6:
        return f"{current_A*1e6:.4f}uA"
    else:
        return f"{current_A*1e9:.4f}nA"


def build_datalog_tasks(device_map, vbat_label, vbat_ch, sample_period):
    """根据 force_map 构造 datalog 任务列表。

    每个设备独立一个 task,vbat 所在设备若未覆盖 vbat 通道,则把 vbat 作为 monitor 追加。
    task 字段结构:
        device_label, inst, force_channels, monitor_channels,
        all_datalog_channels, sample_period, measured_voltages,
        curr_result, error
    """
    task_list = []
    for device_label, (n6705c_inst, hw_channels) in device_map.items():
        monitor_chs = []
        if device_label == vbat_label and vbat_ch not in hw_channels:
            monitor_chs.append(vbat_ch)
        all_datalog_chs = list(hw_channels) + [
            ch for ch in monitor_chs if ch not in hw_channels
        ]
        num_ch = len(all_datalog_chs) or 1
        ch_period = sample_period * num_ch
        task_list.append({
            "device_label": device_label,
            "inst": n6705c_inst,
            "force_channels": list(hw_channels),
            "monitor_channels": monitor_chs,
            "all_datalog_channels": all_datalog_chs,
            "sample_period": ch_period,
            "measured_voltages": None,
            "curr_result": None,
            "error": None,
        })
    return task_list


def run_threads_parallel(task_list, worker_fn, timeout=30):
    """将 worker_fn(idx, task) 并发执行在 task_list 上,返回 errors 列表。"""
    errors = [None] * len(task_list)

    def _wrap(idx, task):
        try:
            worker_fn(idx, task)
        except Exception as e:
            errors[idx] = e

    threads = []
    for idx, task in enumerate(task_list):
        t = threading.Thread(target=_wrap, args=(idx, task), daemon=True)
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=timeout)
    return errors


def configure_datalog_all(active_tasks, test_time, log_fn):
    """串行给每个 task 配置 datalog,失败者标记 task["error"]。"""
    for task in active_tasks:
        try:
            task["inst"].configure_datalog(
                task["all_datalog_channels"], test_time, task["sample_period"]
            )
        except Exception as e:
            task["error"] = str(e)
            log_fn(f"[ERROR] Configure datalog failed on {task['device_label']}: {e}")
    return [t for t in active_tasks if t["error"] is None]


def start_datalog_sync(active_tasks, log_fn, timeout=30):
    """使用 Barrier 让所有设备尽可能同步启动 datalog。"""
    if not active_tasks:
        return
    barrier = threading.Barrier(len(active_tasks), timeout=timeout)

    def _worker(idx, task):
        barrier.wait()
        task["inst"].start_datalog()

    errors = run_threads_parallel(active_tasks, _worker, timeout=timeout)
    for idx, err in enumerate(errors):
        if err:
            dl = active_tasks[idx]["device_label"]
            log_fn(f"[ERROR] Start datalog failed on {dl}: {err}")


def wait_datalog_with_progress(test_time, is_stopped_fn, on_tick):
    """等待 datalog 结束,期间周期性调用 on_tick(frac)。

    返回 True 表示等待完成,False 表示被中止。
    """
    datalog_wait = test_time + 1
    interval = 0.5
    elapsed = 0.0
    while elapsed < datalog_wait:
        if is_stopped_fn():
            return False
        step = min(interval, datalog_wait - elapsed)
        _time.sleep(step)
        elapsed += step
        frac = min(elapsed / datalog_wait, 1.0)
        if on_tick is not None:
            on_tick(frac)
    return not is_stopped_fn()


def fetch_datalog_all(active_tasks, test_time, log_fn, timeout=30):
    """并发 fetch datalog 结果,填入 task["curr_result"]。"""
    def _worker(idx, task):
        task["curr_result"] = task["inst"].fetch_datalog_marker_results(
            task["all_datalog_channels"], test_time
        )

    errors = run_threads_parallel(active_tasks, _worker, timeout=timeout)
    for idx, err in enumerate(errors):
        if err:
            log_fn(
                f"[ERROR] Fetch failed on {active_tasks[idx]['device_label']}: {err}"
            )
    return errors


def restore_force_channels(active_tasks):
    """把 force 过的通道恢复到 VMETer 模式。"""
    for task in active_tasks:
        try:
            task["inst"].restore_channels_to_vmeter(task["force_channels"])
        except Exception:
            pass


def build_summary_payload(device_map, channel_names,
                          vbat_label, vbat_ch,
                          results, vbat_current, vbat_remain,
                          channel_voltages, log_fn,
                          bin_name=""):
    """生成 RESULT / VOLTAGE 日志行并返回 summary dict。"""
    channel_voltages = channel_voltages or {}
    vbat_name = channel_names.get((vbat_label, vbat_ch), "Vbat")

    ordered_keys = []
    for device_label, (_, hw_channels) in device_map.items():
        for ch in hw_channels:
            ordered_keys.append((device_label, ch))

    parts = [f"{vbat_name}: {_format_current_unified(vbat_current)}"]
    for key in ordered_keys:
        name = channel_names.get(key, f"{key[0]}-CH{key[1]}")
        val = results.get(key, 0.0)
        parts.append(f"{name}: {_format_current_unified(val)}")
    if vbat_remain is not None:
        parts.append(f"Vbat_remain: {_format_current_unified(vbat_remain)}")

    prefix = f"[{bin_name}] " if bin_name else ""
    log_fn(f"[RESULT] {prefix}{' | '.join(parts)}")

    voltage_parts = []
    vbat_v = channel_voltages.get((vbat_label, vbat_ch))
    if vbat_v is not None:
        voltage_parts.append(f"{vbat_name}={vbat_v:.4g}V")
    for key in ordered_keys:
        v = channel_voltages.get(key)
        if v is not None:
            name = channel_names.get(key, f"{key[0]}-CH{key[1]}")
            voltage_parts.append(f"{name}={v:.4g}V")
    if voltage_parts:
        log_fn(f"[VOLTAGE] {prefix}{', '.join(voltage_parts)}")

    summary = {
        "vbat": vbat_current,
        "channels": {k: results[k] for k in ordered_keys if k in results},
        "vbat_remain": vbat_remain,
        "channel_voltages": channel_voltages,
    }
    if bin_name:
        summary["bin_name"] = bin_name
    return summary, ordered_keys


__all__ = [
    "CURRENT_UNIT",
    "_UNIT_CONFIG",
    "_format_current_unified",
    "format_current_short",
    "build_datalog_tasks",
    "run_threads_parallel",
    "configure_datalog_all",
    "start_datalog_sync",
    "wait_datalog_with_progress",
    "fetch_datalog_all",
    "restore_force_channels",
    "build_summary_payload",
]
