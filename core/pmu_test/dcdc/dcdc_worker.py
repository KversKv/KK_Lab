# -*- coding: utf-8 -*-
"""
DCDC 效率测试 Worker（仅依赖 PySide6.QtCore，不依赖 QtWidgets）。

从 ui/pages/pmu_test/pmu_dcdc_efficiency.py 平移而来，
纯算法委托 core.pmu_test.dcdc.dcdc_analysis，行为零变更。
"""

import time

from PySide6.QtCore import QThread, Signal

from instruments.mock.mock_instruments import MockN6705C

from .dcdc_analysis import generate_current_points, trimmed_mean


def _measure_point_instant(n, vin_ch, vout_ch, iload_ch, average_cnt):
    if average_cnt <= 1:
        vbat = float(n.measure_voltage(vin_ch))
        vout = float(n.measure_voltage(vout_ch))
        i_in = float(n.measure_current(vin_ch))
        i_out = float(n.measure_current(iload_ch))
    else:
        vbat_acc = 0.0
        vout_acc = 0.0
        i_in_acc = 0.0
        i_out_acc = 0.0
        for _ai in range(average_cnt):
            vbat_acc += float(n.measure_voltage(vin_ch))
            vout_acc += float(n.measure_voltage(vout_ch))
            i_in_acc += float(n.measure_current(vin_ch))
            i_out_acc += float(n.measure_current(iload_ch))
        vbat = vbat_acc / average_cnt
        vout = vout_acc / average_cnt
        i_in = i_in_acc / average_cnt
        i_out = i_out_acc / average_cnt
    return vbat, vout, i_in, i_out


def _measure_point_datalog(n, vin_ch, vout_ch, iload_ch, dlog_duration, debug):
    if debug and isinstance(n, MockN6705C):
        vbat = float(n.measure_voltage(vin_ch))
        vout = float(n.measure_voltage(vout_ch))
        i_in = float(n.measure_current(vin_ch))
        i_out = float(n.measure_current(iload_ch))
        return vbat, vout, i_in, i_out

    sample_period = 0.000060
    curr_channels = [vin_ch, iload_ch]
    volt_channels = [vout_ch]
    curr_result, volt_result = n.fetch_by_datalog(
        curr_channels, volt_channels, dlog_duration, sample_period
    )
    vbat = float(n.measure_voltage(vin_ch))
    vout = volt_result.get(vout_ch, float(n.measure_voltage(vout_ch)))
    i_in = curr_result.get(vin_ch, 0.0)
    i_out = curr_result.get(iload_ch, 0.0)
    return vbat, vout, i_in, i_out


def _run_efficiency_curve(n, cfg, debug, stop_flag_fn,
                          log_fn, chart_point_fn, data_row_fn,
                          baseline_row_fn=None,
                          progress_fn=None, result_update_fn=None,
                          progress_offset=0, progress_total=None,
                          tag="TEST"):
    vin_ch = int(cfg["vin_channel"].replace("CH ", ""))
    vout_ch = int(cfg["vout_channel"].replace("CH ", ""))
    iload_ch = int(cfg["cc_load_channel"].replace("CH ", ""))

    average_cnt = max(1, int(cfg.get("average_cnt", 1)))
    settle_ms = int(cfg.get("settle_time_ms", 3))
    sampling_method = cfg.get("sampling_method", "Instant MEAS")
    dlog_duration = float(cfg.get("dlog_duration_s", 1.0))

    current_points = generate_current_points(cfg)
    current_points_neg = [-abs(c) for c in current_points]

    sleep_settle = 0.0 if debug else 2
    sleep_measure = 0.0 if debug else settle_ms

    n.set_current(iload_ch, 0)
    n.channel_off(iload_ch)
    QThread.msleep(int(sleep_settle * 1000))

    BASELINE_SAMPLES = 5
    i_base_samples = []
    iin_base_samples = []
    vin_base_samples = []
    vout_base_samples = []
    for _bsi in range(BASELINE_SAMPLES):
        i_base_samples.append(float(n.measure_current(iload_ch)))
        iin_base_samples.append(float(n.measure_current(vin_ch)))
        vin_base_samples.append(float(n.measure_voltage(vin_ch)))
        vout_base_samples.append(float(n.measure_voltage(vout_ch)))
        QThread.msleep(int(sleep_measure))

    i_base = trimmed_mean(i_base_samples)
    iin_base = trimmed_mean(iin_base_samples)
    vin_base = trimmed_mean(vin_base_samples)
    vout_base = trimmed_mean(vout_base_samples)

    log_fn(
        f"[{tag}] Baseline ({BASELINE_SAMPLES}x trimmed-mean)  "
        f"Vin={vin_base:.3f}V  Vout={vout_base:.3f}V  "
        f"Iin={iin_base:.6f}A  Iload_base={i_base:.6f}A"
    )
    log_fn(
        f"[{tag}] Iin current samples: "
        f"{[f'{v:.6f}' for v in iin_base_samples]}"
    )
    if baseline_row_fn is not None:
        baseline_row_fn({
            "cc_load": 0.0,
            "efficiency": 0.0,
            "vin": vin_base,
            "iin": iin_base,
            "vout": vout_base,
            "iout": 0.0,
        })

    n.set_current(iload_ch, current_points_neg[0])
    n.channel_on(iload_ch)
    QThread.msleep(int(sleep_settle * 1000))

    output = []
    max_eff = 0.0
    max_eff_iout = 0.0
    sum_eff = 0.0
    sum_vin = 0.0
    sum_vout = 0.0
    total_count = progress_total if progress_total is not None else len(current_points)

    hdr = (f"{'#':>4s}  {'Iset(mA)':>10s}  {'Vin(V)':>8s}  "
           f"{'Vout(V)':>8s}  {'Iin(A)':>10s}  {'Iout(A)':>10s}  "
           f"{'Iload(A)':>10s}  {'Eff(%)':>7s}")
    log_fn(hdr)
    log_fn("-" * len(hdr))

    for idx, i_set in enumerate(current_points):
        if stop_flag_fn():
            log_fn(f"[{tag}] Stopped by user.")
            break

        n.set_current(iload_ch, current_points_neg[idx])
        QThread.msleep(int(sleep_measure))

        if sampling_method == "DataLogger":
            vbat, vout, i_in, i_out = _measure_point_datalog(
                n, vin_ch, vout_ch, iload_ch, dlog_duration, debug
            )
        else:
            vbat, vout, i_in, i_out = _measure_point_instant(
                n, vin_ch, vout_ch, iload_ch, average_cnt
            )

        i_load_actual = max(i_base - i_out, 1e-9)
        denom = vbat * max(i_in - iin_base, 1e-9)
        eff = (vout * i_load_actual) / denom
        eff = max(min(eff, 1.2), 0.0)
        eff_pct = eff * 100

        log_fn(
            f"{idx+1:4d}  {current_points_neg[idx]*1000:10.3f}  {vbat:8.4f}  "
            f"{vout:8.4f}  {i_in:10.6f}  {i_out:10.6f}  "
            f"{i_load_actual:10.6f}  {eff_pct:7.2f}"
        )

        abs_iout = abs(i_out)
        output.append((abs_iout, eff_pct))
        sum_eff += eff_pct
        sum_vin += vbat
        sum_vout += vout
        if eff_pct > max_eff:
            max_eff = eff_pct
            max_eff_iout = abs_iout

        chart_point_fn(abs_iout, eff_pct)

        data_row_fn({
            "cc_load": current_points_neg[idx],
            "efficiency": eff_pct,
            "vin": vbat,
            "iin": i_in,
            "vout": vout,
            "iout": abs_iout,
        })

        if result_update_fn is not None:
            n_pts = len(output)
            result_update_fn({
                "vin": sum_vin / n_pts,
                "vout": sum_vout / n_pts,
                "efficiency": sum_eff / n_pts,
                "max_efficiency": max_eff,
                "max_eff_load": max_eff_iout,
            })

        if progress_fn is not None:
            progress_fn(int((progress_offset + idx + 1) * 100 / total_count))

    n.set_current(iload_ch, 0)
    n.channel_off(iload_ch)

    return output, max_eff, max_eff_iout, sum_eff, sum_vin, sum_vout


class DCDCEfficiencyTestThread(QThread):
    log_message = Signal(str)
    progress = Signal(int)
    chart_point = Signal(float, float)
    chart_clear = Signal()
    result_update = Signal(dict)
    baseline_row = Signal(dict)
    data_row = Signal(dict)
    test_finished = Signal()

    def __init__(self, n6705c, config, debug_flag=False):
        super().__init__()
        self._n6705c = n6705c
        self._cfg = config
        self._debug = debug_flag
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def run(self):
        cfg = self._cfg
        vin_ch = int(cfg["vin_channel"].replace("CH ", ""))
        vout_ch = int(cfg["vout_channel"].replace("CH ", ""))
        iload_ch = int(cfg["cc_load_channel"].replace("CH ", ""))
        n = self._n6705c

        try:
            sweep_mode = cfg["sweep_mode"]
            average_cnt = max(1, int(cfg.get("average_cnt", 1)))
            settle_ms = int(cfg.get("settle_time_ms", 3))
            sampling_method = cfg.get("sampling_method", "Instant MEAS")
            current_points = generate_current_points(cfg)

            self.log_message.emit(
                f"[TEST] Mode: {sweep_mode}, Points: {len(current_points)}, "
                f"Average_CNT: {average_cnt}, Settle: {settle_ms}ms, "
                f"Sampling: {sampling_method}"
            )
            self.log_message.emit(f"[TEST] VIN ch={vin_ch}, VOUT ch={vout_ch}, ILOAD ch={iload_ch}")

            if self._debug and isinstance(n, MockN6705C):
                n._vin_ch = vin_ch
                n._iload_ch = iload_ch

            n.set_mode(vin_ch, "PS2Q")
            n.set_mode(vout_ch, "VMETer")
            n.set_mode(iload_ch, "CCLoad")
            self.log_message.emit(f"[TEST] CH{vin_ch}=PS2Q, CH{vout_ch}=VMETer, CH{iload_ch}=CCLoad")

            n.set_current_limit(vin_ch, 0.5)
            for ch in (vin_ch, vout_ch, iload_ch):
                n.set_channel_range(ch)

            self.chart_clear.emit()
            self.progress.emit(0)

            t_start = time.time()

            output, max_eff, max_eff_iout, sum_eff, sum_vin, sum_vout = _run_efficiency_curve(
                n, cfg, self._debug,
                stop_flag_fn=lambda: self._stop_flag,
                log_fn=self.log_message.emit,
                chart_point_fn=self.chart_point.emit,
                data_row_fn=self.data_row.emit,
                baseline_row_fn=self.baseline_row.emit,
                progress_fn=self.progress.emit,
                result_update_fn=self.result_update.emit,
                tag="TEST",
            )

            elapsed = time.time() - t_start
            minutes, seconds = divmod(elapsed, 60)
            completed = len(output)
            if completed > 0:
                avg = elapsed / completed
                self.log_message.emit(
                    f"[TIME] Total: {int(minutes)}m {seconds:.1f}s | "
                    f"Points: {completed} | Avg: {avg:.2f}s/point"
                )
            else:
                self.log_message.emit(f"[TIME] Total: {int(minutes)}m {seconds:.1f}s")

        except Exception as e:
            self.log_message.emit(f"[ERROR] Test failed: {e}")
        finally:
            try:
                n.set_current(iload_ch, 0)
                n.channel_off(iload_ch)
            except Exception:
                pass
            self.test_finished.emit()


class DCDCVinSweepTestThread(QThread):
    log_message = Signal(str)
    progress = Signal(int)
    chart_point = Signal(float, float)
    chart_clear = Signal()
    chart_new_series = Signal(str)
    result_update = Signal(dict)
    baseline_row = Signal(dict)
    data_row = Signal(dict)
    test_finished = Signal()

    def __init__(self, n6705c, config, debug_flag=False):
        super().__init__()
        self._n6705c = n6705c
        self._cfg = config
        self._debug = debug_flag
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def run(self):
        cfg = self._cfg
        vin_ch = int(cfg["vin_channel"].replace("CH ", ""))
        vout_ch = int(cfg["vout_channel"].replace("CH ", ""))
        iload_ch = int(cfg["cc_load_channel"].replace("CH ", ""))
        n = self._n6705c

        try:
            vin_start = float(cfg.get("vin_start", 3.0))
            vin_end = float(cfg.get("vin_end", 4.2))
            vin_step = float(cfg.get("vin_step", 0.1))

            current_points = generate_current_points(cfg)

            if self._debug and isinstance(n, MockN6705C):
                n._vin_ch = vin_ch
                n._iload_ch = iload_ch

            vin_points = []
            v = vin_start
            while v <= vin_end + vin_step * 0.001:
                vin_points.append(round(v, 4))
                v += vin_step
            if not vin_points:
                vin_points = [vin_start, vin_end]

            total_count = len(vin_points) * len(current_points)
            self.log_message.emit(
                f"[VIN-SWEEP] Vin: {vin_start}V → {vin_end}V, Step: {vin_step}V, "
                f"VIN Points: {len(vin_points)}, Load Points: {len(current_points)}, "
                f"Total: {total_count}"
            )

            n.set_mode(vin_ch, "PS2Q")
            n.set_mode(vout_ch, "VMETer")
            n.set_mode(iload_ch, "CCLoad")

            n.set_current_limit(vin_ch, 0.5)
            for ch in (vin_ch, vout_ch, iload_ch):
                n.set_channel_range(ch)

            self.chart_clear.emit()
            self.progress.emit(0)

            all_output = []
            max_eff = 0.0
            max_eff_iout = 0.0
            sum_eff = 0.0
            done_count = 0

            t_start = time.time()

            for vin_idx, vin_set in enumerate(vin_points):
                if self._stop_flag:
                    self.log_message.emit("[VIN-SWEEP] Stopped by user.")
                    break

                vin_label = f"VIN={vin_set:.2f}V"
                self.chart_new_series.emit(vin_label)
                self.log_message.emit(f"\n[VIN-SWEEP] ── {vin_label} ──")

                n.set_voltage(vin_ch, vin_set)

                output, cur_max_eff, cur_max_eff_iout, cur_sum_eff, _, _ = _run_efficiency_curve(
                    n, cfg, self._debug,
                    stop_flag_fn=lambda: self._stop_flag,
                    log_fn=self.log_message.emit,
                    chart_point_fn=self.chart_point.emit,
                    data_row_fn=self.data_row.emit,
                    baseline_row_fn=None,
                    progress_fn=self.progress.emit,
                    result_update_fn=self.result_update.emit,
                    progress_offset=done_count,
                    progress_total=total_count,
                    tag="VIN-SWEEP",
                )

                all_output.extend(output)
                sum_eff += cur_sum_eff
                done_count += len(output)
                if cur_max_eff > max_eff:
                    max_eff = cur_max_eff
                    max_eff_iout = cur_max_eff_iout

                if self._stop_flag:
                    break

            elapsed = time.time() - t_start
            minutes, seconds = divmod(elapsed, 60)
            completed = len(all_output)
            if completed > 0:
                avg = elapsed / completed
                self.log_message.emit(
                    f"[TIME] Total: {int(minutes)}m {seconds:.1f}s | "
                    f"Points: {completed} | Avg: {avg:.2f}s/point"
                )
            else:
                self.log_message.emit(f"[TIME] Total: {int(minutes)}m {seconds:.1f}s")

        except Exception as e:
            self.log_message.emit(f"[ERROR] VIN Sweep failed: {e}")
        finally:
            try:
                n.set_current(iload_ch, 0)
                n.channel_off(iload_ch)
            except Exception:
                pass
            self.test_finished.emit()


class DCDCTempSweepTestThread(QThread):
    log_message = Signal(str)
    progress = Signal(int)
    chart_point = Signal(float, float)
    chart_clear = Signal()
    result_update = Signal(dict)
    baseline_row = Signal(dict)
    data_row = Signal(dict)
    test_finished = Signal()

    def __init__(self, n6705c, config, debug_flag=False, chamber=None):
        super().__init__()
        self._n6705c = n6705c
        self._cfg = config
        self._debug = debug_flag
        self._chamber = chamber
        self._stop_flag = False

    def request_stop(self):
        self._stop_flag = True

    def run(self):
        cfg = self._cfg
        vin_ch = int(cfg["vin_channel"].replace("CH ", ""))
        vout_ch = int(cfg["vout_channel"].replace("CH ", ""))
        iload_ch = int(cfg["cc_load_channel"].replace("CH ", ""))
        n = self._n6705c
        vt = self._chamber

        try:
            temp_start = float(cfg.get("temp_start", -40))
            temp_end = float(cfg.get("temp_end", 85))
            temp_step = float(cfg.get("temp_step", 25))
            fixed_load_a = abs(float(cfg.get("fixed_load_a", 0.1)))
            average_cnt = max(1, int(cfg.get("average_cnt", 1)))
            settle_ms = int(cfg.get("settle_time_ms", 3))
            sampling_method = cfg.get("sampling_method", "Instant MEAS")
            dlog_duration = float(cfg.get("dlog_duration_s", 1.0))

            if self._debug and isinstance(n, MockN6705C):
                n._vin_ch = vin_ch
                n._iload_ch = iload_ch

            temp_points = []
            t = temp_start
            while t <= temp_end + temp_step * 0.001:
                temp_points.append(round(t, 1))
                t += temp_step
            if not temp_points:
                temp_points = [temp_start, temp_end]

            sleep_settle = 0.0 if self._debug else 2
            sleep_measure = 0.0 if self._debug else settle_ms

            self.log_message.emit(
                f"[TEMP-SWEEP] Temp: {temp_start}°C → {temp_end}°C, Step: {temp_step}°C, "
                f"Points: {len(temp_points)}, Fixed Load: {fixed_load_a*1000:.1f}mA"
            )

            if vt is not None:
                self.log_message.emit("[TEMP-SWEEP] Chamber connected - automatic temperature control enabled.")
                try:
                    vt.start()
                    self.log_message.emit("[TEMP-SWEEP] Chamber power ON.")
                except Exception as e:
                    self.log_message.emit(f"[TEMP-SWEEP] Chamber start warning: {e}")
            else:
                self.log_message.emit(
                    "[TEMP-SWEEP] No chamber connected. "
                    "Temperature must be set manually for each point."
                )

            n.set_mode(vin_ch, "PS2Q")
            n.set_mode(vout_ch, "VMETer")
            n.set_mode(iload_ch, "CCLoad")

            n.set_current_limit(vin_ch, 0.5)
            for ch in (vin_ch, vout_ch, iload_ch):
                n.set_channel_range(ch)

            n.set_current(iload_ch, -fixed_load_a)
            n.channel_on(iload_ch)
            QThread.msleep(int(sleep_settle * 1000))

            self.chart_clear.emit()
            self.progress.emit(0)

            output = []
            max_eff = 0.0
            max_eff_temp = 0.0
            sum_eff = 0.0
            total_count = len(temp_points)

            hdr = (f"{'#':>4s}  {'Temp(°C)':>10s}  {'Vin(V)':>8s}  "
                   f"{'Vout(V)':>8s}  {'Iin(A)':>10s}  {'Iout(A)':>10s}  "
                   f"{'Eff(%)':>7s}")
            self.log_message.emit(hdr)
            self.log_message.emit("-" * len(hdr))

            TEMP_TOLERANCE = 1.0
            TEMP_SETTLE_POLL_S = 2.0
            TEMP_SETTLE_TIMEOUT_S = 600

            t_start = time.time()

            for idx, temp_set in enumerate(temp_points):
                if self._stop_flag:
                    self.log_message.emit("[TEMP-SWEEP] Stopped by user.")
                    break

                if vt is not None:
                    self.log_message.emit(f"[TEMP-SWEEP] Setting chamber to {temp_set}°C ...")
                    try:
                        vt.set_temperature(temp_set)
                    except Exception as e:
                        self.log_message.emit(f"[TEMP-SWEEP] Set temp error: {e}")

                    settle_start = time.time()
                    settled = False
                    while not settled:
                        if self._stop_flag:
                            break
                        try:
                            actual = vt.get_current_temp()
                        except Exception:
                            actual = None

                        if actual is not None and abs(actual - temp_set) <= TEMP_TOLERANCE:
                            self.log_message.emit(
                                f"[TEMP-SWEEP] Chamber stable at {actual:.1f}°C (target {temp_set}°C)."
                            )
                            settled = True
                        else:
                            elapsed_settle = time.time() - settle_start
                            if elapsed_settle > TEMP_SETTLE_TIMEOUT_S:
                                self.log_message.emit(
                                    f"[TEMP-SWEEP] Timeout waiting for {temp_set}°C "
                                    f"(current: {actual}°C). Measuring anyway."
                                )
                                settled = True
                            else:
                                actual_str = f"{actual:.1f}" if actual is not None else "N/A"
                                self.log_message.emit(
                                    f"[TEMP-SWEEP] Waiting... current={actual_str}°C, "
                                    f"target={temp_set}°C, elapsed={elapsed_settle:.0f}s"
                                )
                                QThread.msleep(int(TEMP_SETTLE_POLL_S * 1000))

                    if self._stop_flag:
                        break
                    QThread.msleep(int(sleep_settle * 1000))
                else:
                    self.log_message.emit(f"[TEMP-SWEEP] Measuring at {temp_set}°C (manual) ...")
                    QThread.msleep(int(sleep_settle * 1000))

                if sampling_method == "DataLogger":
                    vbat, vout, i_in, i_out = _measure_point_datalog(
                        n, vin_ch, vout_ch, iload_ch, dlog_duration, self._debug
                    )
                else:
                    vbat, vout, i_in, i_out = _measure_point_instant(
                        n, vin_ch, vout_ch, iload_ch, average_cnt
                    )

                i_load_actual = abs(i_out)
                p_in = vbat * abs(i_in)
                p_out = vout * i_load_actual
                eff = p_out / max(p_in, 1e-12)
                eff = max(min(eff, 1.2), 0.0)
                eff_pct = eff * 100

                self.log_message.emit(
                    f"{idx+1:4d}  {temp_set:10.1f}  {vbat:8.4f}  "
                    f"{vout:8.4f}  {i_in:10.6f}  {i_out:10.6f}  "
                    f"{eff_pct:7.2f}"
                )

                output.append((temp_set, eff_pct))
                sum_eff += eff_pct
                if eff_pct > max_eff:
                    max_eff = eff_pct
                    max_eff_temp = temp_set

                self.chart_point.emit(temp_set, eff_pct)

                self.data_row.emit({
                    "cc_load": -fixed_load_a,
                    "efficiency": eff_pct,
                    "vin": vbat,
                    "iin": i_in,
                    "vout": vout,
                    "iout": i_load_actual,
                })

                n_pts = len(output)
                self.result_update.emit({
                    "vin": vbat,
                    "vout": vout,
                    "efficiency": sum_eff / n_pts,
                    "max_efficiency": max_eff,
                    "max_eff_load": max_eff_temp,
                })

                self.progress.emit(int((idx + 1) * 100 / total_count))

            elapsed = time.time() - t_start
            minutes, seconds = divmod(elapsed, 60)
            completed = len(output)
            if completed > 0:
                avg = elapsed / completed
                self.log_message.emit(
                    f"[TIME] Total: {int(minutes)}m {seconds:.1f}s | "
                    f"Points: {completed} | Avg: {avg:.2f}s/point"
                )
            else:
                self.log_message.emit(f"[TIME] Total: {int(minutes)}m {seconds:.1f}s")

        except Exception as e:
            self.log_message.emit(f"[ERROR] Temp Sweep failed: {e}")
        finally:
            try:
                n.set_current(iload_ch, 0)
                n.channel_off(iload_ch)
            except Exception:
                pass
            self.test_finished.emit()
