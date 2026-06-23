# -*- coding: utf-8 -*-
"""
IsGain 测试 Worker（仅依赖 PySide6.QtCore，不依赖 QtWidgets）。

从 ui/pages/pmu_test/pmu_isGain_ui.py 的 _IsGainTestWorker 平移而来，
算法/解析委托 core.pmu_test.isgain.isgain_analysis，行为零变更。
"""

import base64
import time

from PySide6.QtCore import QObject, Signal

from .isgain_analysis import (
    YSCALE_SEQUENCE,
    RECOVERY_SCALE,
    parse_channel,
    prev_scale,
    analyze_results,
)


class IsGainTestWorker(QObject):
    log = Signal(str)
    progress = Signal(int)
    result_row = Signal(dict)
    summary = Signal(dict)
    finished = Signal()
    error = Signal(str)

    MODE_SINGLE = "single"
    MODE_TRAVERSE = "traverse"

    def __init__(self, n6705c, scope, config, test_mode="single"):
        super().__init__()
        self.n6705c = n6705c
        self.scope = scope
        self.config = config
        self.test_mode = test_mode
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def _interruptible_sleep(self, seconds):
        interval = 0.1
        elapsed = 0.0
        while elapsed < seconds and not self._stop_flag:
            time.sleep(min(interval, seconds - elapsed))
            elapsed += interval

    def _measure_with_autoscale(self, ripple_ch, label=""):
        voltage = None
        ripple = None

        try:
            voltage = self.scope.get_channel_mean(ripple_ch)
        except Exception as e:
            self.log.emit(f"  [WARN] Voltage measurement failed: {e}")
            voltage = None

        if self._stop_flag:
            return voltage, ripple

        try:
            ripple = self.scope.get_channel_pk2pk(ripple_ch)
        except Exception as e:
            self.log.emit(f"  [WARN] Ripple measurement failed: {e}")
            ripple = None

        if voltage is not None and ripple is not None:
            self.log.emit(f"  Voltage (CH{ripple_ch} Mean) = {voltage:.6f} V")
            self.log.emit(f"  Ripple  (CH{ripple_ch} Pk2Pk) = {ripple:.6f} V")
            return voltage, ripple

        if self._stop_flag:
            return voltage, ripple

        self.log.emit(f"  [AUTO-SCALE] {label}Measurement failed, starting recovery...")

        try:
            orig_scale = self.scope.get_channel_scale(ripple_ch)
        except Exception:
            orig_scale = 0.020

        try:
            self.scope.set_channel_scale(ripple_ch, RECOVERY_SCALE)
            self.scope.set_channel_offset(ripple_ch, 0.0)
            self.log.emit(f"  [AUTO-SCALE] {label}Set scale={RECOVERY_SCALE} V/div, offset=0 for coarse measurement")
            self._interruptible_sleep(0.3)
            if self._stop_flag:
                return voltage, ripple

            self.scope.run()
            self._interruptible_sleep(0.8)
            if self._stop_flag:
                return voltage, ripple
            self.scope.stop()
            self._interruptible_sleep(0.2)
        except Exception as e:
            self.log.emit(f"  [WARN] Recovery setup failed: {e}")
            return voltage, ripple

        voltage_t = None
        ripple_t = None
        try:
            voltage_t = self.scope.get_channel_mean(ripple_ch)
        except Exception:
            pass
        try:
            ripple_t = self.scope.get_channel_pk2pk(ripple_ch)
        except Exception:
            pass

        if voltage_t is None:
            self.log.emit(f"  [WARN] {label}Cannot get voltage even at {RECOVERY_SCALE} V/div, aborting auto-scale")
            try:
                self.scope.set_channel_scale(ripple_ch, orig_scale)
                self.scope.set_channel_offset(ripple_ch, 0.0)
            except Exception:
                pass
            return voltage, ripple

        rip_str = f"{ripple_t:.6f}" if ripple_t is not None else "N/A"
        self.log.emit(f"  [AUTO-SCALE] {label}Coarse Voltage_T = {voltage_t:.6f} V, Ripple_T = {rip_str} V")

        voltage = voltage_t
        ripple = ripple_t

        scale = RECOVERY_SCALE
        while True:
            if self._stop_flag:
                break

            smaller = prev_scale(scale, YSCALE_SEQUENCE)
            if smaller is None or smaller < orig_scale * 0.99:
                break

            offset_val = voltage_t - 0.03
            try:
                self.scope.set_channel_scale(ripple_ch, smaller)
                self.scope.set_channel_offset(ripple_ch, offset_val)
                self.log.emit(f"  [AUTO-SCALE] {label}Trying scale={smaller} V/div, offset={offset_val:.4f} V")
                self._interruptible_sleep(0.2)
                if self._stop_flag:
                    break

                self.scope.run()
                self._interruptible_sleep(0.6)
                if self._stop_flag:
                    break
                self.scope.stop()
                self._interruptible_sleep(0.2)
            except Exception as e:
                self.log.emit(f"  [WARN] {label}Scale adjustment failed: {e}")
                break

            v_try = None
            r_try = None
            try:
                v_try = self.scope.get_channel_mean(ripple_ch)
            except Exception:
                pass
            try:
                r_try = self.scope.get_channel_pk2pk(ripple_ch)
            except Exception:
                pass

            if v_try is not None and r_try is not None:
                voltage = v_try
                ripple = r_try
                scale = smaller
            else:
                self.log.emit(f"  [AUTO-SCALE] {label}Measurement failed at scale={smaller} V/div, using previous result")
                try:
                    self.scope.set_channel_scale(ripple_ch, scale)
                    self.scope.set_channel_offset(ripple_ch, voltage_t - 0.03)
                except Exception:
                    pass
                break

        if voltage is not None:
            self.log.emit(f"  Voltage (CH{ripple_ch} Mean) = {voltage:.6f} V")
        if ripple is not None:
            self.log.emit(f"  Ripple  (CH{ripple_ch} Pk2Pk) = {ripple:.6f} V")

        return voltage, ripple

    def _run_single_sweep(self, load_ch, ripple_ch, current_steps, step_offset=0, total_override=None, reg_value=None):
        total = total_override if total_override else (len(current_steps) + 1)
        results = []
        save_screenshot = self.config.get("save_screenshot", True)

        self.log.emit("[STEP 0] Measuring 0-load baseline (channel OFF)...")
        self.n6705c.channel_off(load_ch)
        self._interruptible_sleep(1.0)
        if self._stop_flag:
            self.log.emit("[TEST] Test aborted by user.")
            return False, results, None

        try:
            self.scope.set_AutoRipple_test(ripple_ch)
        except Exception as e:
            self.log.emit(f"  [WARN] set_AutoRipple_test failed: {e}")

        self._interruptible_sleep(0.5)

        v0 = None
        r0 = None

        screenshot_b64 = None
        if not self._stop_flag:
            try:
                self._interruptible_sleep(0.1)
                if save_screenshot and not self._stop_flag:
                    self.scope.stop()
                    self._interruptible_sleep(0.5)

                if not self._stop_flag:
                    v0, r0 = self._measure_with_autoscale(ripple_ch, label="0-load ")

                if save_screenshot and not self._stop_flag:
                    png_data = self.scope.capture_screen_png()
                    screenshot_b64 = base64.b64encode(png_data).decode("ascii")
                    self.log.emit("  Screenshot captured (0-load)")
            except Exception as e:
                self.log.emit(f"  [WARN] Measurement/Screenshot failed: {e}")
            finally:
                if save_screenshot:
                    try:
                        self.scope.run()
                    except Exception:
                        pass

        zero_row = {
            "step": step_offset,
            "load_current": 0.0,
            "voltage": v0,
            "ripple": r0,
            "v_drop": 0.0,
            "screenshot_b64": screenshot_b64,
            "remark": "0-load baseline",
        }
        if reg_value is not None:
            zero_row["reg_value"] = reg_value
        self.result_row.emit(zero_row)
        results.append(zero_row)
        self.progress.emit(int((step_offset + 1) / total * 100))

        self.n6705c.channel_on(load_ch)
        self._interruptible_sleep(0.5)

        for i, current_a in enumerate(current_steps):
            if self._stop_flag:
                self.log.emit("[TEST] Test aborted by user.")
                return False, results, v0

            global_step = step_offset + i + 1
            prefix = f"Reg={reg_value}, " if reg_value is not None else ""
            self.log.emit(f"[STEP {global_step}/{total}] {prefix}Load = {current_a} A")
            self.n6705c.set_current(load_ch, -abs(current_a))
            self._interruptible_sleep(0.1)

            voltage = None
            ripple = None
            sc_b64 = None

            if not self._stop_flag:
                try:
                    self._interruptible_sleep(0.1)
                    if save_screenshot and not self._stop_flag:
                        self.scope.stop()
                        self._interruptible_sleep(0.1)

                    if not self._stop_flag:
                        voltage, ripple = self._measure_with_autoscale(ripple_ch)

                    if save_screenshot and not self._stop_flag:
                        png_data = self.scope.capture_screen_png()
                        sc_b64 = base64.b64encode(png_data).decode("ascii")
                        self.log.emit(f"  Screenshot captured (step {global_step})")
                except Exception as e:
                    self.log.emit(f"  [WARN] Measurement/Screenshot failed: {e}")
                finally:
                    if save_screenshot:
                        try:
                            self.scope.run()
                        except Exception:
                            pass

            v_drop = None
            if v0 is not None and voltage is not None:
                v_drop = v0 - voltage

            row = {
                "step": global_step,
                "load_current": current_a,
                "voltage": voltage,
                "ripple": ripple,
                "v_drop": v_drop,
                "screenshot_b64": sc_b64,
            }
            if reg_value is not None:
                row["reg_value"] = reg_value
            self.result_row.emit(row)
            results.append(row)
            self.progress.emit(int((global_step + 1) / total * 100))

        return True, results, v0

    def run(self):
        load_ch = None
        try:
            cfg = self.config
            load_ch = parse_channel(cfg["load_channel"])
            ripple_ch = parse_channel(cfg["ripple_channel"])

            start_i = abs(cfg["is_gain_start_current"])
            end_i = abs(cfg["is_gain_end_current"])
            step_i = abs(cfg["is_gain_step_current"])

            if start_i > end_i:
                start_i, end_i = end_i, start_i

            if step_i < 1e-9:
                self.error.emit("Step Current must be greater than 0.")
                return

            current_steps = []
            cur = start_i
            while cur <= end_i + 1e-9:
                current_steps.append(round(cur, 6))
                cur += step_i

            if not current_steps:
                self.error.emit("No current steps generated. Check Start/End/Step Current.")
                return

            self.n6705c.set_mode(load_ch, "CCLoad")
            self.n6705c.set_current(load_ch, 0)

            t_start = time.time()
            total_steps = 0

            if self.test_mode == self.MODE_SINGLE:
                total = len(current_steps) + 1
                total_steps = total
                self.log.emit(f"[TEST] Single Is_gain test: {total} steps (including 0-load)")
                self.log.emit(f"[TEST] Load CH{load_ch}, Ripple CH{ripple_ch}")
                ok, results, v0 = self._run_single_sweep(load_ch, ripple_ch, current_steps, total_override=total)

                if v0 is None and results:
                    v0 = results[0].get("voltage")
                analysis = analyze_results(results, v0)
                self.summary.emit(analysis)

            elif self.test_mode == self.MODE_TRAVERSE:
                msb = cfg["is_gain_msb"]
                lsb = cfg["is_gain_lsb"]
                reg_values = list(range(lsb, msb + 1))

                if not reg_values:
                    self.error.emit("No register values to traverse. Check MSB >= LSB.")
                    return

                steps_per_reg = len(current_steps) + 1
                total = len(reg_values) * steps_per_reg
                total_steps = total
                self.log.emit(f"[TEST] Traverse Is_gain: {len(reg_values)} reg values x {steps_per_reg} steps = {total} total")
                self.log.emit(f"[TEST] Register range: {lsb} ~ {msb}, Current: {start_i} A ~ {end_i} A step {step_i} A")

                all_results = []
                for reg_idx, reg_val in enumerate(reg_values):
                    if self._stop_flag:
                        self.log.emit("[TEST] Test aborted by user.")
                        break

                    self.log.emit(f"[REG] Setting register value = {reg_val}")
                    offset = reg_idx * steps_per_reg
                    ok, results, v0 = self._run_single_sweep(
                        load_ch, ripple_ch, current_steps,
                        step_offset=offset, total_override=total, reg_value=reg_val,
                    )
                    all_results.extend(results)
                    if not ok:
                        break

                if all_results:
                    v0 = all_results[0].get("voltage")
                    analysis = analyze_results(all_results, v0)
                    self.summary.emit(analysis)

            elapsed = time.time() - t_start
            minutes, seconds = divmod(elapsed, 60)
            if total_steps > 0:
                avg = elapsed / total_steps
                self.log.emit(f"[TIME] Total: {int(minutes)}m {seconds:.1f}s | Steps: {total_steps} | Avg: {avg:.2f}s/step")
            else:
                self.log.emit(f"[TIME] Total: {int(minutes)}m {seconds:.1f}s")

        except Exception as e:
            self.error.emit(str(e))
        finally:
            if load_ch is not None:
                try:
                    self.n6705c.set_current(load_ch, 0)
                    self.n6705c.channel_off(load_ch)
                    self.log.emit("[TEST] Load current reset to 0 A. Test completed.")
                except Exception as e:
                    self.log.emit(f"[WARN] Cleanup failed: {e}")
            self.finished.emit()
