#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import random
import threading
import time
from PySide6.QtCore import QObject, Signal
from instruments.mock.mock_instruments import MockN6705C
from instruments.power.keysight.n6705c import N6705C
from instruments.power.keysight.n6705c_datalog_process import parse_csv_text, parse_dlog_binary
from log_config import get_logger

logger = get_logger(__name__)

class _ScanWorker(QObject):
    device_found = Signal(str, str, str, str)
    finished = Signal()
    error = Signal(str)

    def run(self):
        try:
            from core.n6705c.search_worker import discover_n6705c_details
            for detail in discover_n6705c_details():
                res = detail["resource"]
                idn = detail.get("idn", "")
                parts = idn.split(",")
                model = parts[1].strip() if len(parts) > 1 else "N6705C"
                serial = detail.get("serial") or "Unknown"
                ip = res.split("::")[1] if "::" in res else res
                self.device_found.emit(serial, model, ip, res)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class _ConnectWorker(QObject):
    success = Signal(object, str, str)
    finished = Signal()
    error = Signal(str)

    def __init__(self, visa_resource, serial, debug=False):
        super().__init__()
        self._visa_resource = visa_resource
        self._serial = serial
        self._debug = debug

    def run(self):
        n6705c = None
        try:
            if self._debug:
                n6705c = MockN6705C()
                idn = "MOCK,N6705C,MOCK"
            else:
                n6705c = N6705C(self._visa_resource)
                idn = n6705c.instr.query("*IDN?").strip()
                if "N6705C" not in idn:
                    raise RuntimeError(f"Device mismatch: {idn}")
            logger.debug("Datalog connect worker verified IDN: %s", idn)
            self.success.emit(n6705c, self._serial, self._visa_resource)
        except Exception as e:
            if n6705c is not None:
                try:
                    n6705c.disconnect()
                except Exception:
                    pass
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class _DatalogWorker(QObject):
    data_ready = Signal(dict)
    dlog_raw_ready = Signal(list)
    finished = Signal()
    error = Signal(str)
    progress_update = Signal(int, str)

    def __init__(self, n6705c_list, channels_per_unit, unit_labels,
                 record_type, sample_period_us, monitoring_time_s,
                 debug=False, voltage_channels_per_unit=None):
        super().__init__()
        self.n6705c_list = n6705c_list
        self.channels_per_unit = channels_per_unit
        self.unit_labels = unit_labels
        self.record_type = record_type
        self.sample_period_us = sample_period_us
        self.monitoring_time_s = monitoring_time_s
        self.debug = debug
        self.voltage_channels_per_unit = voltage_channels_per_unit or [[] for _ in n6705c_list]
        self._is_stopped = False

    def stop(self):
        self._is_stopped = True

    def run(self):
        try:
            run_start = time.time()
            sample_period_s = self.sample_period_us / 1_000_000.0

            if self.debug:
                all_data = self._run_mock(sample_period_s, run_start)
                self.data_ready.emit(all_data)
                self.finished.emit()
                return

            active_units = self._collect_active_units()
            if not active_units:
                self.finished.emit()
                return

            self._configure_units(active_units, sample_period_s, run_start)
            self._wait_capture(active_units, run_start)
            all_data, raw_dlog_list = self._download_units(sample_period_s, run_start)

            self.progress_update.emit(98, "Processing results...")
            logger.debug("[Datalog][Progress] Emitting results at %.3fs", time.time() - run_start)
            logger.info("[Datalog] Total channels with data: %d", len(all_data))
            self.dlog_raw_ready.emit(raw_dlog_list)
            self.data_ready.emit(all_data)
            self.progress_update.emit(100, "Done")
            logger.debug("[Datalog][Progress] Total run time: %.3fs", time.time() - run_start)
            self.finished.emit()
        except Exception as e:
            logger.error("[Datalog] ERROR: %s", e, exc_info=True)
            self.error.emit(str(e))
            self.finished.emit()

    def _run_mock(self, sample_period_s, run_start):
        """Mock 模式：生成假数据并推进进度条。"""
        self.progress_update.emit(5, "Generating mock data...")
        logger.debug("[Datalog][Progress] Mock mode start at %.3fs", time.time() - run_start)
        mock_start = time.time()
        all_data = self._generate_mock_data(sample_period_s)
        logger.debug("[Datalog][Progress] Mock data generated in %.3fs", time.time() - mock_start)
        self.progress_update.emit(100, "Done")
        return all_data

    def _collect_active_units(self):
        """筛选出有勾选电流或电压通道的仪器单元。"""
        active_units = []
        for unit_idx, n6705c in enumerate(self.n6705c_list):
            curr_channels = self.channels_per_unit[unit_idx]
            volt_channels = self.voltage_channels_per_unit[unit_idx]
            if curr_channels or volt_channels:
                active_units.append((unit_idx, n6705c, curr_channels, volt_channels))
        return active_units

    def _configure_units(self, active_units, sample_period_s, run_start):
        """多线程并行配置各仪器，并用 Barrier 对齐后再同时 INIT:DLOG。"""
        self.progress_update.emit(2, "Configuring instruments...")
        logger.debug("[Datalog][Progress] Configure start at %.3fs", time.time() - run_start)
        config_start = time.time()

        barrier = threading.Barrier(len(active_units), timeout=30)
        init_errors = [None] * len(active_units)

        def configure_and_start(idx, unit_idx, n6705c, curr_channels, volt_channels):
            try:
                time.sleep(0.3)
                try:
                    n6705c.instr.query("*OPC?")
                except Exception:
                    pass
                n6705c.instr.write("*CLS")
                try:
                    n6705c.instr.write("ABOR:DLOG")
                except Exception:
                    pass

                for ch in range(1, 5):
                    n6705c.instr.write(f"SENS:DLOG:FUNC:CURR OFF,(@{ch})")
                    n6705c.instr.write(f"SENS:DLOG:FUNC:VOLT OFF,(@{ch})")

                for ch in curr_channels:
                    n6705c.instr.write(f"SENS:DLOG:FUNC:CURR ON,(@{ch})")
                    n6705c.instr.write(f"SENS:DLOG:CURR:RANG:AUTO ON,(@{ch})")

                for ch in volt_channels:
                    n6705c.instr.write(f"SENS:DLOG:FUNC:VOLT ON,(@{ch})")

                n6705c.instr.write(f"SENS:DLOG:TIME {self.monitoring_time_s}")
                n6705c.instr.write(f"SENS:DLOG:PER {sample_period_s}")
                n6705c.instr.write("TRIG:DLOG:SOUR IMM")

                dlog_file = f"internal:\\datalog_cap_{unit_idx}.dlog"

                barrier.wait()

                n6705c.instr.write(f'INIT:DLOG "{dlog_file}"')
                logger.debug("[Datalog] Unit %d INIT:DLOG sent at %.6f", unit_idx, time.time())
            except Exception as e:
                init_errors[idx] = e

        threads = []
        for idx, (unit_idx, n6705c, curr_ch, volt_ch) in enumerate(active_units):
            t = threading.Thread(
                target=configure_and_start,
                args=(idx, unit_idx, n6705c, curr_ch, volt_ch),
                daemon=True,
            )
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        logger.debug("[Datalog][Progress] Configure done in %.3fs", time.time() - config_start)

    def _wait_capture(self, active_units, run_start):
        """等待仪器完成采集：优先 STAT:OPER:COND 探测，失败降级为固定时长等待。

        期间处理用户停止（ABOR:DLOG）、长采集保活（*IDN?）与进度推进。
        """
        self.progress_update.emit(2, "Capturing data...")
        logger.debug("[Datalog][Progress] Capture wait start at %.3fs", time.time() - run_start)

        safety_buffer = max(0.5, min(5.0, self.monitoring_time_s * 0.3))
        capture_total = self.monitoring_time_s + safety_buffer
        logger.info("[Datalog] Waiting up to %.2fs for capture (monitor=%.2fs + buffer=%.2fs)...",
                    capture_total, self.monitoring_time_s, safety_buffer)
        capture_start = time.time()
        hard_deadline = capture_start + self.monitoring_time_s + max(safety_buffer, 5.0)
        keepalive_interval = 300
        last_keepalive = time.time()
        poll_sleep = 0.05 if self.monitoring_time_s <= 2.0 else 0.2
        measuring_bit = 0x1000

        probe_channels = []
        for unit_idx, n6705c, curr_ch, volt_ch in active_units:
            any_ch = None
            if curr_ch:
                any_ch = curr_ch[0]
            elif volt_ch:
                any_ch = volt_ch[0]
            probe_channels.append(any_ch)

        probe_enabled = all(ch is not None for ch in probe_channels)
        probe_failures = 0
        probe_max_failures = 2

        def _is_unit_done(n6705c, channel):
            resp = n6705c.instr.query(f"STAT:OPER:COND? (@{channel})")
            cond = int(float(resp.strip()))
            return (cond & measuring_bit) == 0

        while True:
            now = time.time()
            elapsed = now - capture_start

            if self._is_stopped:
                logger.info("[Datalog] Stopped by user during capture wait, aborting datalog and fetching data...")
                self.progress_update.emit(90, "Stopping instruments...")
                for unit_idx, n6705c, _, _ in active_units:
                    try:
                        n6705c.instr.write("ABOR:DLOG")
                        logger.debug("[Datalog] ABOR:DLOG sent to unit %d", unit_idx)
                    except Exception as e:
                        logger.error("[Datalog] Failed to abort dlog on unit %d: %s", unit_idx, e)
                time.sleep(0.3)
                break

            if probe_enabled and elapsed >= self.monitoring_time_s:
                try:
                    all_done = True
                    for (unit_idx, n6705c, _, _), ch in zip(active_units, probe_channels):
                        if not _is_unit_done(n6705c, ch):
                            all_done = False
                            break
                    if all_done:
                        logger.debug("[Datalog] All units reported capture complete at %.3fs", elapsed)
                        break
                except Exception as e:
                    probe_failures += 1
                    logger.warning("[Datalog] STAT:OPER:COND probe failed (%d/%d): %s",
                                   probe_failures, probe_max_failures, e)
                    if probe_failures >= probe_max_failures:
                        probe_enabled = False
                        logger.warning("[Datalog] Disabling early-completion probe, falling back to fixed wait")

            if elapsed >= capture_total:
                if not probe_enabled or now >= hard_deadline:
                    logger.debug("[Datalog] Capture wait reached capture_total at %.3fs", elapsed)
                    break

            if now - last_keepalive >= keepalive_interval:
                for unit_idx, n6705c, _, _ in active_units:
                    try:
                        n6705c.instr.query("*IDN?")
                        logger.debug("[Datalog] Keep-alive query sent to unit %d", unit_idx)
                    except Exception as e:
                        logger.warning("[Datalog] Keep-alive failed on unit %d: %s", unit_idx, e)
                last_keepalive = now

            capture_pct = min(elapsed / capture_total, 1.0) if capture_total > 0 else 1.0
            overall_pct = int(2 + capture_pct * 91)
            self.progress_update.emit(overall_pct, "Capturing data...")
            time.sleep(poll_sleep)

        logger.debug("[Datalog][Progress] Capture wait done in %.3fs", time.time() - capture_start)

    def _download_units(self, sample_period_s, run_start):
        """逐台下载 dlog 数据：优先二进制直读（重试4次），失败降级 CSV 导出。"""
        self.progress_update.emit(93, "Downloading data...")
        logger.debug("[Datalog][Progress] Download start at %.3fs", time.time() - run_start)
        download_start = time.time()

        all_data = {}
        raw_dlog_list = []

        for unit_idx, n6705c in enumerate(self.n6705c_list):
            curr_channels = self.channels_per_unit[unit_idx]
            volt_channels = self.voltage_channels_per_unit[unit_idx]
            if not curr_channels and not volt_channels:
                continue

            ulabel = self.unit_labels[unit_idx]
            unit_data = None

            dlog_file = f"internal:\\datalog_cap_{unit_idx}.dlog"
            self._wait_flush_ready(n6705c, unit_idx)

            raw_dlog = None
            read_attempts = 4
            read_timeout_ms = 8000
            for attempt in range(read_attempts):
                saved_to = None
                try:
                    try:
                        saved_to = n6705c.instr.timeout
                        n6705c.instr.timeout = read_timeout_ms
                    except Exception:
                        saved_to = None
                    try:
                        n6705c.instr.write("*CLS")
                    except Exception:
                        pass
                    t0 = time.time()
                    raw_dlog = n6705c.read_mmem_data(dlog_file)
                    t1 = time.time()
                    if isinstance(raw_dlog, bytes) and len(raw_dlog) > 0:
                        logger.info("[Datalog] dlog downloaded: %d bytes in %.1fs (attempt %d)",
                                    len(raw_dlog), t1 - t0, attempt + 1)
                        raw_dlog_list.append(raw_dlog)
                        unit_data = parse_dlog_binary(
                            raw_dlog, curr_channels, volt_channels,
                            ulabel, sample_period_s
                        )
                        break
                    else:
                        logger.warning("[Datalog] dlog read returned empty on attempt %d", attempt + 1)
                except Exception as e:
                    logger.warning("[Datalog] dlog download failed on attempt %d/%d: %s",
                                   attempt + 1, read_attempts, e)
                finally:
                    if saved_to is not None:
                        try:
                            n6705c.instr.timeout = saved_to
                        except Exception:
                            pass
                time.sleep(min(0.5 * (attempt + 1), 1.5))

            if not unit_data:
                unit_data = self._download_csv_fallback(
                    n6705c, unit_idx, curr_channels, volt_channels,
                    ulabel, sample_period_s,
                )

            if unit_data:
                all_data.update(unit_data)

        logger.debug("[Datalog][Progress] Download done in %.3fs", time.time() - download_start)
        return all_data, raw_dlog_list

    @staticmethod
    def _wait_flush_ready(n6705c, unit_idx, opc_timeout_ms=4000, settle_s=0.25):
        """等待仪器把 dlog 缓存刷到内部文件系统（*OPC? + 短暂静置）。"""
        saved = None
        try:
            try:
                saved = n6705c.instr.timeout
                n6705c.instr.timeout = opc_timeout_ms
            except Exception:
                saved = None
            try:
                n6705c.instr.write("*CLS")
            except Exception:
                pass
            try:
                n6705c.instr.query("*OPC?")
                logger.debug("[Datalog] *OPC? returned for unit %d", unit_idx)
            except Exception as e:
                logger.warning("[Datalog] *OPC? wait failed on unit %d: %s", unit_idx, e)
        finally:
            if saved is not None:
                try:
                    n6705c.instr.timeout = saved
                except Exception:
                    pass
        time.sleep(settle_s)

    def _download_csv_fallback(self, n6705c, unit_idx, curr_channels,
                               volt_channels, ulabel, sample_period_s):
        """二进制 dlog 直读失败时，改为让仪器导出 CSV 再下载解析。"""
        logger.info("[Datalog] Falling back to CSV export...")
        csv_file = f"internal:\\datalog_cap_{unit_idx}.csv"
        n6705c.instr.write(f'MMEM:EXP:DLOG "{csv_file}"')
        for _ in range(15):
            time.sleep(0.2)

        t0 = time.time()
        raw_csv = n6705c.read_mmem_data(csv_file)
        t1 = time.time()
        if isinstance(raw_csv, bytes):
            csv_text = raw_csv.decode('ascii', errors='replace')
        else:
            csv_text = raw_csv
        logger.info("[Datalog] CSV download: %d chars in %.1fs", len(csv_text), t1 - t0)

        return parse_csv_text(
            csv_text, curr_channels, volt_channels,
            ulabel, sample_period_s
        )

    def _generate_mock_data(self, sample_period_s):
        rng = random.Random(42)
        total_points = int(self.monitoring_time_s / sample_period_s)
        total_points = min(total_points, 50000)

        all_data = {}
        ch_global_idx = 0
        for unit_idx in range(len(self.channels_per_unit)):
            curr_channels = self.channels_per_unit[unit_idx]
            volt_channels = self.voltage_channels_per_unit[unit_idx]
            ulabel = self.unit_labels[unit_idx]

            all_chs = sorted(set(curr_channels) | set(volt_channels))
            for ch in all_chs:
                if ch in volt_channels:
                    label = f"{ulabel} CH{ch} V".strip()
                    t = [i * sample_period_s for i in range(total_points)]
                    base_mV = 1200 + ch_global_idx * 600
                    values = [
                        base_mV
                        + 5 * math.sin(2 * math.pi * 0.3 * ti)
                        + rng.gauss(0, 3)
                        for ti in t
                    ]
                    all_data[label] = {"time": t, "values": values}
                    ch_global_idx += 1

                if ch in curr_channels:
                    label = f"{ulabel} CH{ch} I".strip()
                    t = [i * sample_period_s for i in range(total_points)]
                    base_mA = 1780 + ch_global_idx * 120
                    noise_std = 15 + ch_global_idx * 5
                    values = [
                        base_mA
                        + 8 * math.sin(2 * math.pi * 0.5 * ti)
                        + rng.gauss(0, noise_std)
                        for ti in t
                    ]
                    all_data[label] = {"time": t, "values": values}
                    ch_global_idx += 1

        return all_data
