# -*- coding: utf-8 -*-
"""
CLK 测试纯算法/解析函数（无 PySide6，可 pytest 直测）。

从 ui/pages/pmu_test/clk_test_ui.py 的 _CLKTestWorker 平移而来，
行为零变更；self.log.emit → log_fn 可选回调；self.config → 参数传入。
"""

import math
import os
import re
import shutil
import statistics


def simulate_frequency(x, nominal=32768.0, gain=1.0, noise=0.5):
    base = nominal + x * gain
    ripple = math.sin(x / 5.0) * noise
    return base + ripple


def float_range(start, end, step):
    arr = []
    if step <= 0:
        return arr
    if start <= end:
        x = start
        while x <= end + 1e-9:
            arr.append(round(x, 3))
            x += step
    else:
        x = start
        while x >= end - 1e-9:
            arr.append(round(x, 3))
            x -= step
    return arr


def parse_tek_csv(lines):
    data_rows = []
    header_found = False
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("name,type"):
            header_found = True
            continue
        if not header_found:
            continue
        parts = line.split(",")
        if len(parts) >= 5:
            try:
                timestamp = float(parts[3])
                delta = float(parts[4])
                data_rows.append((timestamp, delta))
            except ValueError:
                continue

    if len(data_rows) < 3:
        raise ValueError("Insufficient data rows in TekScope CSV")

    samples = []
    i = 1
    while i < len(data_rows) - 1:
        _, d1 = data_rows[i]
        _, d2 = data_rows[i + 1]
        if d1 > 0 and d2 > 0:
            full_period = d1 + d2
            mid_time = data_rows[i][0] + d1 / 2.0
            samples.append((mid_time, full_period))
        i += 2

    return samples


def parse_dslogic_csv(lines, log_fn=None):
    sample_rate = None
    edges = []
    data_started = False

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith(";"):
            lower = line.lower()
            if "sample rate" in lower:
                parts = lower.split(":")
                if len(parts) >= 2:
                    rate_str = parts[-1].strip()
                    rate_str = rate_str.replace("mhz", "e6").replace("khz", "e3").replace("ghz", "e9")
                    rate_str = rate_str.replace("m samples", "").replace("samples", "").strip()
                    try:
                        sample_rate = float(rate_str)
                    except ValueError:
                        m = re.search(r'([\d.]+)\s*(mhz|khz|ghz|hz)', lower)
                        if m:
                            val = float(m.group(1))
                            unit = m.group(2)
                            mul = {"hz": 1, "khz": 1e3, "mhz": 1e6, "ghz": 1e9}
                            sample_rate = val * mul.get(unit, 1)
            continue
        if line.lower().startswith("time"):
            data_started = True
            continue
        if not data_started:
            continue

        parts = line.split(",")
        if len(parts) >= 2:
            try:
                t = float(parts[0])
                level = int(parts[1].strip())
                edges.append((t, level))
            except (ValueError, IndexError):
                continue

    if sample_rate and log_fn:
        log_fn(f"[INFO] DSLogic Sample Rate = {sample_rate / 1e6:.3f} MHz")

    rising_times = []
    for i in range(len(edges)):
        if edges[i][1] == 1:
            if i == 0 or edges[i - 1][1] == 0:
                rising_times.append(edges[i][0])

    if len(rising_times) < 2:
        raise ValueError("Insufficient rising edge data in DSLogic CSV")

    samples = []
    for i in range(1, len(rising_times)):
        period = rising_times[i] - rising_times[i - 1]
        if period > 0:
            mid_time = (rising_times[i - 1] + rising_times[i]) / 2.0
            samples.append((mid_time, period))

    return samples


def parse_generic_csv(lines):
    samples = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        parts = line.split(",")
        try:
            if len(parts) >= 2:
                t = float(parts[0])
                period = float(parts[1])
                if period > 0:
                    samples.append((t, period))
            elif len(parts) == 1:
                period = float(parts[0])
                if period > 0:
                    samples.append((len(samples), period))
        except ValueError:
            continue
    return samples


def find_sigrok_cli():
    path = shutil.which("sigrok-cli")
    if path:
        return path
    common_paths = [
        r"C:\Program Files\sigrok\sigrok-cli\sigrok-cli.exe",
        r"C:\Program Files (x86)\sigrok\sigrok-cli\sigrok-cli.exe",
        r"C:\sigrok\sigrok-cli.exe",
    ]
    for p in common_paths:
        if os.path.isfile(p):
            return p
    return None


def analyze_clk_perf(samples, ble_min_time=0.1, log_fn=None):
    if not samples:
        raise ValueError("No valid sample data")

    periods = [p for _, p in samples if p > 0]
    if not periods:
        raise ValueError("No valid period data")

    n = len(periods)
    avg_period = statistics.mean(periods)
    avg_freq = 1.0 / avg_period
    min_period = min(periods)
    max_period = max(periods)
    min_freq = 1.0 / max_period
    max_freq = 1.0 / min_period

    period_jitter_pp = (max_period - min_period) * 1e9
    period_std = statistics.pstdev(periods) * 1e9 if n > 1 else 0.0

    c2c_diffs = [abs(periods[i] - periods[i - 1]) for i in range(1, n)]
    c2c_jitter_max = max(c2c_diffs) * 1e9 if c2c_diffs else 0.0
    c2c_jitter_rms = (statistics.mean([d ** 2 for d in c2c_diffs]) ** 0.5) * 1e9 if c2c_diffs else 0.0

    cum_errors = []
    ideal_accum = 0.0
    real_accum = 0.0
    for p in periods:
        ideal_accum += avg_period
        real_accum += p
        cum_errors.append((real_accum - ideal_accum) * 1e9)
    tie_max = max(abs(e) for e in cum_errors) if cum_errors else 0.0

    times = [t for t, _ in samples if _ > 0]
    if n >= 10:
        seg = max(1, n // 10)
        first_freqs = [1.0 / p for p in periods[:seg]]
        last_freqs = [1.0 / p for p in periods[-seg:]]
        freq_first = statistics.mean(first_freqs)
        freq_last = statistics.mean(last_freqs)
        freq_drift_ppm = (freq_last - freq_first) / avg_freq * 1_000_000.0
        total_time = times[-1] - times[0] if len(times) > 1 else 1.0
        freq_drift_ppm_per_s = freq_drift_ppm / total_time if total_time > 0 else 0.0
    else:
        freq_drift_ppm = 0.0
        freq_drift_ppm_per_s = 0.0

    if log_fn:
        log_fn("=" * 60)
        log_fn("[PERF] ===== Clock Performance Analysis =====")
        log_fn("=" * 60)
        log_fn(f"[PERF] Total Periods      = {n}")
        log_fn(f"[PERF] Avg Frequency       = {avg_freq:.6f} Hz")
        log_fn(f"[PERF] Avg Period          = {avg_period * 1e6:.6f} us")
        log_fn("-" * 60)
        log_fn(f"[PERF] Min Period          = {min_period * 1e6:.6f} us  ({min_freq:.4f} Hz)")
        log_fn(f"[PERF] Max Period          = {max_period * 1e6:.6f} us  ({max_freq:.4f} Hz)")
        log_fn("-" * 60)
        log_fn(f"[PERF] Period Jitter (P-P) = {period_jitter_pp:.3f} ns")
        log_fn(f"[PERF] Period Std Dev      = {period_std:.3f} ns")
        log_fn("-" * 60)
        log_fn(f"[PERF] Cycle-to-Cycle Max  = {c2c_jitter_max:.3f} ns")
        log_fn(f"[PERF] Cycle-to-Cycle RMS  = {c2c_jitter_rms:.3f} ns")
        log_fn("-" * 60)
        log_fn(f"[PERF] TIE Max (Accum Err) = {tie_max:.3f} ns")
        log_fn("-" * 60)
        log_fn(f"[PERF] Freq Drift          = {freq_drift_ppm:+.3f} ppm (total)")
        log_fn(f"[PERF] Freq Drift Rate     = {freq_drift_ppm_per_s:+.4f} ppm/s")
        log_fn("=" * 60)

    total_time = times[-1] - times[0] if len(times) > 1 else sum(periods)

    if total_time >= ble_min_time:
        if log_fn:
            log_fn("")
            log_fn("=" * 60)
            log_fn("[BLE] ===== Bluetooth Clock Suitability Analysis =====")
            log_fn("[BLE] (Ref: Bluetooth Core Spec Vol 6, Part B, 4.2.2)")
            log_fn("[BLE] SCA = Clock intrinsic stability (relative to its own average)")
            log_fn("=" * 60)
            log_fn(f"[BLE] Measured Avg Freq     = {avg_freq:.6f} Hz (as reference)")
            log_fn(f"[BLE] Total Measure Time   = {total_time:.3f} s")
            log_fn(f"[BLE] Freq Drift           = {freq_drift_ppm:+.3f} ppm")
            log_fn("-" * 60)

        ble_windows = [0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 4.0]
        worst_stability_ppm = abs(freq_drift_ppm)

        if log_fn:
            log_fn("[BLE] Window Stability Analysis (relative to own average):")
        for win in ble_windows:
            n_per_win = int(round(win / avg_period))
            if n_per_win < 1 or n_per_win >= n:
                continue
            ideal_time = n_per_win * avg_period
            max_err = 0.0
            for i in range(0, n - n_per_win + 1, max(1, (n - n_per_win) // 500)):
                actual_time = sum(periods[i:i + n_per_win])
                err_ppm = abs(actual_time - ideal_time) / ideal_time * 1_000_000.0
                if err_ppm > max_err:
                    max_err = err_ppm
            if max_err > worst_stability_ppm:
                worst_stability_ppm = max_err
            if log_fn:
                log_fn(f"[BLE]   Window={win*1000:>7.1f} ms  |  Max Deviation={max_err:>8.3f} ppm")

        if log_fn:
            log_fn("-" * 60)
            log_fn(f"[BLE] Worst-case Stability = {worst_stability_ppm:.3f} ppm")
            log_fn("-" * 60)

        sca_thresholds = [
            (7, 20,  "0-20 ppm"),
            (6, 30,  "21-30 ppm"),
            (5, 50,  "31-50 ppm"),
            (4, 75,  "51-75 ppm"),
            (3, 100, "76-100 ppm"),
            (2, 150, "101-150 ppm"),
            (1, 250, "151-250 ppm"),
            (0, 500, "251-500 ppm"),
        ]

        matched_sca = None
        for sca_val, limit, label in sca_thresholds:
            if worst_stability_ppm <= limit:
                matched_sca = (sca_val, limit, label)
                break

        ble_ok = worst_stability_ppm <= 500.0
        ble_sym = "✅" if ble_ok else "❌"
        ble_str = "PASS" if ble_ok else "FAIL"

        if log_fn:
            log_fn(f"[BLE] BLE SCA Compliance (≤ ±500 ppm): {ble_sym} {ble_str}  ({worst_stability_ppm:.3f} ppm)")

            if matched_sca:
                sca_val, limit, label = matched_sca
                log_fn(f"[BLE] SCA Field Value      = {sca_val} ({label})")
            else:
                log_fn(f"[BLE] SCA Field Value      = N/A (exceeds ±500 ppm, not BLE compliant)")

            log_fn("-" * 60)
            log_fn("[BLE] SCA Level Reference Table (Bluetooth Core Spec):")
            log_fn("[BLE]   SCA=7: 0-20 ppm    (Best, minimum window widening)")
            log_fn("[BLE]   SCA=6: 21-30 ppm")
            log_fn("[BLE]   SCA=5: 31-50 ppm   (Recommended for Master/Central)")
            log_fn("[BLE]   SCA=4: 51-75 ppm")
            log_fn("[BLE]   SCA=3: 76-100 ppm")
            log_fn("[BLE]   SCA=2: 101-150 ppm")
            log_fn("[BLE]   SCA=1: 151-250 ppm")
            log_fn("[BLE]   SCA=0: 251-500 ppm (Worst, maximum window widening)")
            log_fn("-" * 60)

            if matched_sca:
                sca_val, _, _ = matched_sca
                conn_interval_s = 1.0
                peer_sca_ppm = 50.0
                own_sca_ppm = worst_stability_ppm
                combined_sca = own_sca_ppm + peer_sca_ppm
                window_widening_us = combined_sca * conn_interval_s * 2
                log_fn(f"[BLE] Window Widening Estimate (Connection Interval = {conn_interval_s*1000:.0f}ms, Peer SCA = ±{peer_sca_ppm:.0f} ppm):")
                log_fn(f"[BLE]   Combined SCA        = ±{combined_sca:.1f} ppm")
                log_fn(f"[BLE]   Window Widening     = {window_widening_us:.1f} us")
                log_fn(f"[BLE]   (Formula: widening = (masterSCA + slaveSCA) × timeSinceLastAnchor × 2)")

            log_fn("=" * 60)
    else:
        if log_fn:
            log_fn(f"[INFO] Data duration {total_time:.2f}s < {ble_min_time:.1f}s, skipping Bluetooth suitability analysis (requires >= {ble_min_time:.1f}s)")

    points = []
    for t, p in samples:
        if p > 0:
            freq = 1.0 / p
            ppm = (freq - avg_freq) / avg_freq * 1_000_000.0
            points.append({"x": t, "freq": freq, "ppm": ppm})

    return {
        "mode": "clk_perf",
        "data": points,
        "summary": {
            "avg_freq": avg_freq,
            "avg_period_us": avg_period * 1e6,
            "min_freq": min_freq,
            "max_freq": max_freq,
            "min_period_us": min_period * 1e6,
            "max_period_us": max_period * 1e6,
            "period_jitter_pp_ns": period_jitter_pp,
            "period_std_ns": period_std,
            "c2c_jitter_max_ns": c2c_jitter_max,
            "c2c_jitter_rms_ns": c2c_jitter_rms,
            "tie_max_ns": tie_max,
            "freq_drift_ppm": freq_drift_ppm,
            "freq_drift_ppm_per_s": freq_drift_ppm_per_s,
        }
    }
