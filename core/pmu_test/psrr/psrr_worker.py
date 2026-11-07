# -*- coding: utf-8 -*-
"""PSRR 扫频 Worker，仅依赖 QtCore。"""
from __future__ import annotations

import math
import subprocess
import time

from PySide6.QtCore import QObject, Signal, Slot

from log_config import get_logger
from .audio_precision_session import (
    AudioPrecisionSSHSession,
    build_remote_script,
    ssh_command,
)
from .psrr_analysis import (
    AudioPrecisionPSRRConfig,
    PSRRConfig,
    acquisition_settle_seconds,
    audio_precision_config_from_dict,
    calculate_psrr_db,
    calculate_psrr_from_dbv,
    config_from_dict,
    scope_timebase_seconds,
    simulate_psrr_point,
    spectrum_level_at_frequency,
    summarize_results,
)

logger = get_logger(__name__)


class PSRRTestWorker(QObject):
    progress = Signal(int)
    point_ready = Signal(object)
    result_ready = Signal(object)
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, config: dict | PSRRConfig, n6705c=None, oscilloscope=None,
                 mock_mode: bool = False, parent=None):
        super().__init__(parent)
        self.config = config if isinstance(config, PSRRConfig) else config_from_dict(config)
        self.config.validate()
        self.n6705c = n6705c
        self.oscilloscope = oscilloscope
        self.mock_mode = mock_mode
        self._abort = False
        self._points: list[dict] = []

    def stop(self):
        self._abort = True

    def _sleep(self, seconds: float) -> bool:
        deadline = time.monotonic() + max(0.0, seconds)
        while not self._abort:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            time.sleep(min(0.05, remaining))
        return False

    @Slot()
    def start(self):
        success = False
        message = "测试停止"
        try:
            self.log.emit(
                f"[INFO] MSO64B + J2120A PSRR sweep: "
                f"{len(self.config.frequencies_hz)} points, "
                f"AFG amplitude={self.config.afg_amplitude_mvpp:g} mVpp"
            )
            if self.mock_mode:
                self._run_mock()
            else:
                self._run_real()
            complete = len(self._points) == len(self.config.frequencies_hz)
            success = complete and not self._abort and bool(self._points)
            message = "测试完成" if success else "测试停止"
        except Exception as exc:
            logger.error("PSRR 测试执行失败", exc_info=True)
            message = str(exc)
            self.log.emit(f"[ERROR] {message}")
        finally:
            if self._points:
                summary = summarize_results(self._points, self.config.limit_db)
                self.result_ready.emit({
                    "points": list(self._points),
                    "summary": summary,
                    "config": self._config_dict(),
                    "mock_mode": self.mock_mode,
                    "success": success,
                })
            self.progress.emit(100 if success else 0)
            self.finished.emit(success, message)

    def _config_dict(self) -> dict:
        return {
            "measurement_method": "mso64b_j2120a",
            "source_channel": self.config.source_channel,
            "input_channel": self.config.input_channel,
            "output_channel": self.config.output_channel,
            "dc_voltage": self.config.dc_voltage,
            "afg_amplitude_mvpp": self.config.afg_amplitude_mvpp,
            "start_frequency_hz": self.config.frequencies_hz[0],
            "end_frequency_hz": self.config.frequencies_hz[-1],
            "frequency_points": len(self.config.frequencies_hz),
            "frequencies_hz": list(self.config.frequencies_hz),
            "cycles": self.config.cycles,
            "output_scale_mv": self.config.output_scale_mv,
            "limit_db": self.config.limit_db,
            "close_channel_after": self.config.close_channel_after,
        }

    def _run_mock(self):
        self.log.emit("[MOCK] 使用确定性纹波数据验证扫频与结果链路")
        for index, frequency in enumerate(self.config.frequencies_hz):
            if self._abort or not self._sleep(0.08):
                break
            point = simulate_psrr_point(frequency, self.config.nominal_input_vrms)
            self._emit_point(point, index)

    def _run_real(self):
        if self.n6705c is None or self.oscilloscope is None:
            raise RuntimeError("请先连接 N6705C 与 MSO64B")
        if not all(hasattr(self.oscilloscope, name) for name in ("set_afg_sine", "set_afg_output")):
            raise RuntimeError("当前示波器不是受支持的 MSO64B，缺少 AFG 接口")

        channel = self.config.source_channel
        was_on = bool(self.n6705c.get_channel_state(channel))
        original_voltage = float(self.n6705c.measure_voltage(channel))
        self.log.emit(
            f"[INFO] Source CH{channel}: DC={self.config.dc_voltage:g} V, "
            f"MSO64B AFG → J2120A, scope input CH{self.config.input_channel}, "
            f"output CH{self.config.output_channel}"
        )
        try:
            self.n6705c.set_voltage(channel, self.config.dc_voltage)
            if not was_on:
                self.n6705c.channel_on(channel)
            for index, frequency in enumerate(self.config.frequencies_hz):
                if self._abort:
                    break
                self._measure_real_point(frequency, index)
        finally:
            try:
                self.oscilloscope.set_afg_output(False)
            except Exception:
                logger.error("PSRR 测试关闭 MSO64B AFG 失败", exc_info=True)
                self.log.emit("[ERROR] MSO64B AFG 关闭失败，请检查仪器输出")
            try:
                self.n6705c.set_voltage(channel, original_voltage)
                if self.config.close_channel_after or not was_on:
                    self.n6705c.channel_off(channel)
            except Exception:
                logger.error("PSRR 测试恢复 N6705C 状态失败", exc_info=True)
                self.log.emit("[ERROR] N6705C 状态恢复失败，请检查仪器输出")

    def _measure_real_point(self, frequency: float, index: int):
        self.oscilloscope.set_afg_sine(
            amplitude_vpp=self.config.afg_amplitude_vpp,
            frequency_hz=frequency,
            offset_v=0.0,
            output_on=True,
        )
        preview_timebase = 1.1 / frequency / 10.0
        final_timebase = scope_timebase_seconds(frequency, self.config.cycles)
        input_scale = max(self.config.afg_amplitude_vpp / 8.0, 1e-6)
        output_scale = self.config.output_scale_mv / 1000.0
        scope = self.oscilloscope
        scope.run()
        scope.set_timebase_scale(preview_timebase)
        for scope_channel, scale in (
            (self.config.input_channel, input_scale),
            (self.config.output_channel, output_scale),
        ):
            scope.set_channel_display(scope_channel, True)
            scope.set_channel_coupling(scope_channel, "AC")
            scope.set_channel_scale(scope_channel, scale)
            scope.set_channel_offset(scope_channel, 0.0)
        scope.set_trigger_config(self.config.input_channel, 0.0, "POS")
        if not self._sleep(acquisition_settle_seconds(preview_timebase)):
            return

        scope.run()
        scope.set_timebase_scale(final_timebase)
        if not self._sleep(acquisition_settle_seconds(final_timebase)):
            return
        input_vrms = float(scope.get_channel_rms(self.config.input_channel))
        output_vrms = float(scope.get_channel_rms(self.config.output_channel))
        if not all(math.isfinite(value) and 0 < value < 1e30
                   for value in (input_vrms, output_vrms)):
            raise RuntimeError(f"{frequency:g} Hz 纹波测量值无效，请检查探头与量程")
        point = {
            "frequency_hz": frequency,
            "input_vrms": input_vrms,
            "output_vrms": output_vrms,
            "psrr_db": calculate_psrr_db(input_vrms, output_vrms),
        }
        self._emit_point(point, index)

    def _emit_point(self, point: dict, index: int):
        self._points.append(point)
        self.point_ready.emit(dict(point))
        self.progress.emit(round((index + 1) * 100 / len(self.config.frequencies_hz)))
        if index == 0:
            self.log.emit(
                f"{'Freq (Hz)':>12}\t{'VIN (mVrms)':>18}\t"
                f"{'VOUT (mVrms)':>18}\t{'PSRR (dB)':>12}"
            )
        self.log.emit(
            f"{point['frequency_hz']:>12.6g}\t"
            f"{point['input_vrms'] * 1000:>18.4f}\t"
            f"{point['output_vrms'] * 1000:>18.4f}\t"
            f"{point['psrr_db']:>12.3f}"
        )


class AudioPrecisionConnectionWorker(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    log = Signal(str)

    def __init__(self, config: AudioPrecisionPSRRConfig | None = None,
                 operation: str = "connect", target=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.operation = operation
        self.target = target

    @Slot()
    def run(self):
        try:
            if self.operation == "disconnect":
                self._disconnect()
                self.succeeded.emit(None)
                return
            if self.config is None:
                raise ValueError("Audio Precision connection config is required")
            from debug_config import DEBUG_MOCK
            if DEBUG_MOCK or self.config.connection_mode == "local":
                target = self._connect_local()
            else:
                target = AudioPrecisionSSHSession(self.config)
                target.connect(self._on_remote_event)
            self.target = target
            self.succeeded.emit(target)
        except Exception as exc:
            logger.error("Audio Precision 连接操作失败", exc_info=True)
            self.failed.emit(str(exc))

    def _connect_local(self):
        from instruments.factory import create_audio_precision
        ap = create_audio_precision()
        try:
            ap.connect()
            if not ap.connected:
                raise RuntimeError("Audio Precision did not enter the connected state")
            if bool(getattr(getattr(ap, "apx", None), "IsDemoMode", False)):
                raise RuntimeError("APx500 is in Demo Mode; check the APx USB connection")
            return ap
        except Exception:
            try:
                ap.disconnect()
            except Exception:
                logger.error("Audio Precision 连接失败后的清理失败", exc_info=True)
            raise

    def _disconnect(self):
        if self.target is None:
            return
        if isinstance(self.target, AudioPrecisionSSHSession):
            self.target.disconnect()
            self.log.emit("[INFO] Audio Precision SSH disconnected")
            return
        try:
            self.target.set_psrr_generator_off()
        except Exception:
            logger.error("Audio Precision 断连前关闭发生器失败", exc_info=True)
            self.log.emit("[ERROR] AP generator off failed before disconnect")
        self.target.disconnect()
        self.log.emit("[INFO] Audio Precision disconnected")

    def _on_remote_event(self, event: dict):
        if event.get("type") == "log":
            self.log.emit(f"[GUEST] {event.get('message', '')}")


class AudioPrecisionOutputWorker(QObject):
    log = Signal(str)
    finished = Signal(bool, bool, str)

    def __init__(self, config: AudioPrecisionPSRRConfig, enabled: bool,
                 audio_precision=None,
                 ssh_session: AudioPrecisionSSHSession | None = None, parent=None):
        super().__init__(parent)
        self.config = config
        self.enabled = bool(enabled)
        self.audio_precision = audio_precision
        self.ssh_session = ssh_session

    @Slot()
    def run(self):
        try:
            if self.ssh_session is not None:
                self.ssh_session.set_output(
                    self.config, self.enabled, self._on_remote_event
                )
            else:
                self._set_local_output()
            state = "ON" if self.enabled else "OFF"
            self.finished.emit(True, self.enabled, f"Audio Precision OUTPUT {state}")
        except Exception as exc:
            logger.error("Audio Precision OUTPUT 操作失败", exc_info=True)
            self.finished.emit(False, self.enabled, str(exc))

    def _set_local_output(self):
        ap = self.audio_precision
        if ap is None or not ap.connected:
            raise RuntimeError("Audio Precision is not connected")
        if not self.enabled:
            ap.set_psrr_generator_off()
            return
        if self.config.project_path:
            ap.open_project(self.config.project_path)
        ap.configure_psrr_measurement(
            self.config.signal_path,
            self.config.measurement,
            output_channel=self.config.output_channel,
            amplitude_vrms=self.config.amplitude_vrms,
            offset_v=self.config.offset_v,
            bandwidth_hz=self.config.bandwidth_hz,
            generator_on=True,
        )

    def _on_remote_event(self, event: dict):
        if event.get("type") == "log":
            self.log.emit(f"[GUEST] {event.get('message', '')}")


class AudioPrecisionPSRRWorker(QObject):
    progress = Signal(int)
    point_ready = Signal(object)
    result_ready = Signal(object)
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, config: dict | AudioPrecisionPSRRConfig,
                 audio_precision=None, mock_mode: bool = False,
                 ssh_session: AudioPrecisionSSHSession | None = None, parent=None):
        super().__init__(parent)
        self.config = (
            config if isinstance(config, AudioPrecisionPSRRConfig)
            else audio_precision_config_from_dict(config)
        )
        self.config.validate()
        self.audio_precision = audio_precision
        self.ssh_session = ssh_session
        self.mock_mode = mock_mode
        self._owns_audio_precision = False
        self._remote_process = None
        self._abort = False
        self._points: list[dict] = []

    def stop(self):
        self._abort = True
        if self.ssh_session is not None:
            self.ssh_session.terminate()
            return
        process = self._remote_process
        if process is not None and process.poll() is None:
            process.terminate()

    def _sleep(self, seconds: float) -> bool:
        deadline = time.monotonic() + max(0.0, seconds)
        while not self._abort:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return True
            time.sleep(min(0.05, remaining))
        return False

    @Slot()
    def start(self):
        success = False
        message = "测试停止"
        try:
            self.log.emit(
                f"[INFO] Audio Precision connection: {self.config.connection_mode}, "
                f"target={self._connection_target()}"
            )
            self.log.emit(
                f"[INFO] Audio Precision PSRR sweep: "
                f"project={self.config.project_path or '<current>'}, "
                f"signal path={self.config.signal_path}, measurement={self.config.measurement}, "
                f"VIN=INPUT{self.config.vin_input_channel}, "
                f"VOUT=INPUT{self.config.vout_input_channel}, "
                f"output=CH{self.config.output_channel}, "
                f"amplitude={self.config.amplitude_vrms * 1000:g} mVrms, "
                f"offset={self.config.offset_v:g} V, "
                f"bandwidth={self.config.bandwidth_hz:g} Hz, "
                f"FFT length={self.config.fft_length}, "
                f"window={self.config.fft_window}, "
                f"averages={self.config.fft_averages}, "
                f"points={len(self.config.frequencies_hz)}"
            )
            if self.mock_mode:
                self._run_mock()
            else:
                self._run_real()
            complete = len(self._points) == len(self.config.frequencies_hz)
            success = complete and not self._abort and bool(self._points)
            message = "测试完成" if success else "测试停止"
        except Exception as exc:
            logger.error("Audio Precision PSRR 测试执行失败", exc_info=True)
            message = str(exc)
            self.log.emit(f"[ERROR] {message}")
        finally:
            if not self.mock_mode:
                success, message = self._cleanup_audio_precision(success, message)
            if self._points:
                self.result_ready.emit({
                    "points": list(self._points),
                    "summary": summarize_results(self._points, self.config.limit_db),
                    "config": self._config_dict(),
                    "mock_mode": self.mock_mode,
                    "success": success,
                })
            self.progress.emit(100 if success else 0)
            self.finished.emit(success, message)

    def _run_mock(self):
        self.log.emit("[MOCK] 使用确定性双通道 FFT 数据验证 Audio Precision 扫频链路")
        for index, frequency in enumerate(self.config.frequencies_hz):
            if self._abort or not self._sleep(0.08):
                break
            point = simulate_psrr_point(frequency, self.config.amplitude_vrms)
            point.update({
                "input_dbv": 20.0 * math.log10(point["input_vrms"]),
                "output_dbv": 20.0 * math.log10(point["output_vrms"]),
                "input_dc_v": self.config.offset_v,
                "output_dc_v": 1.8,
                "input_fft_frequency_hz": frequency,
                "output_fft_frequency_hz": frequency,
            })
            self._emit_point(point, index)

    def _run_real(self):
        if self.config.connection_mode == "vm_ssh":
            self._run_remote()
            return
        if self.audio_precision is None:
            from instruments.factory import create_audio_precision
            self.audio_precision = create_audio_precision()
            self._owns_audio_precision = True
        ap = self.audio_precision
        if not ap.connected:
            ap.connect()
        if self.config.project_path:
            ap.open_project(self.config.project_path)
        resolved = ap.configure_psrr_measurement(
            self.config.signal_path,
            self.config.measurement,
            output_channel=self.config.output_channel,
            amplitude_vrms=self.config.amplitude_vrms,
            offset_v=self.config.offset_v,
            bandwidth_hz=self.config.bandwidth_hz,
            generator_on=None,
        )
        measurement = resolved or self.config.measurement
        self.log.emit(
            f"[INFO] AP VIN=INPUT{self.config.vin_input_channel}, "
            f"VOUT=INPUT{self.config.vout_input_channel}; "
            "HP=DC, LP=ADC passband, Weighting=None, EQ=None"
        )
        for index, frequency in enumerate(self.config.frequencies_hz):
            if self._abort:
                break
            self._measure_real_point(frequency, index, measurement)

    def _connection_target(self) -> str:
        if self.config.connection_mode == "local":
            return "local AP"
        if self.config.ssh_profile:
            return self.config.ssh_profile
        return f"{self.config.ssh_user}@{self.config.ssh_host}:{self.config.ssh_port}"

    def _remote_script(self) -> str:
        return build_remote_script(self.config)

    def _run_remote(self):
        if self.ssh_session is not None:
            self.log.emit(f"[INFO] Using connected Guest AP session: {self._connection_target()}")
            self.ssh_session.run_sweep(self.config, self._on_remote_session_event)
            return
        command = ssh_command(self.config)
        self.log.emit(f"[INFO] Starting Guest AP worker: {self._connection_target()}")
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        self._remote_process = process
        completed = False
        try:
            process.stdin.write(self._remote_script())
            process.stdin.close()
            for raw_line in process.stdout:
                line = raw_line.strip()
                if not line:
                    continue
                if not line.startswith("KK_LAB_PSRR_EVENT:"):
                    self.log.emit(f"[GUEST] {line}")
                    continue
                event = json.loads(base64.b64decode(line.split(":", 1)[1]).decode("utf-8"))
                event_type = event.get("type")
                if event_type == "point":
                    self._emit_point(event["point"], int(event["index"]))
                elif event_type == "log":
                    self.log.emit(f"[GUEST] {event['message']}")
                elif event_type == "error":
                    raise RuntimeError(event["message"])
                elif event_type == "complete":
                    completed = True
            return_code = process.wait()
            if self._abort:
                return
            if return_code != 0:
                raise RuntimeError(f"Guest AP worker exited with code {return_code}")
            if not completed:
                raise RuntimeError("Guest AP worker ended without a completion event")
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process.stdout is not None:
                process.stdout.close()
            self._remote_process = None

    def _on_remote_session_event(self, event: dict):
        event_type = event.get("type")
        if event_type == "point":
            self._emit_point(event["point"], int(event["index"]))
        elif event_type == "log":
            self.log.emit(f"[GUEST] {event.get('message', '')}")

    def _measure_real_point(self, frequency: float, index: int, measurement: str):
        ap = self.audio_precision
        ap.set_psrr_generator_frequency(frequency)
        input_frequencies, input_levels = ap.get_signal_analyzer_fft_data(
            self.config.signal_path, measurement,
            channel=self.config.vin_input_channel - 1, run=True,
            fft_length=self.config.fft_length,
            fft_window=self.config.fft_window,
            fft_averages=self.config.fft_averages,
        )
        output_frequencies, output_levels = ap.get_signal_analyzer_fft_data(
            self.config.signal_path, measurement,
            channel=self.config.vout_input_channel - 1, run=False,
        )
        input_bin_hz, input_dbv = spectrum_level_at_frequency(
            input_frequencies, input_levels, frequency
        )
        output_bin_hz, output_dbv = spectrum_level_at_frequency(
            output_frequencies, output_levels, frequency
        )
        dc_levels = ap.get_psrr_input_dc_levels(self.config.signal_path)
        input_dc_v = dc_levels[self.config.vin_input_channel - 1]
        output_dc_v = dc_levels[self.config.vout_input_channel - 1]
        point = {
            "frequency_hz": frequency,
            "input_dbv": input_dbv,
            "output_dbv": output_dbv,
            "input_vrms": 10.0 ** (input_dbv / 20.0),
            "output_vrms": 10.0 ** (output_dbv / 20.0),
            "input_dc_v": input_dc_v,
            "output_dc_v": output_dc_v,
            "input_fft_frequency_hz": input_bin_hz,
            "output_fft_frequency_hz": output_bin_hz,
            "psrr_db": calculate_psrr_from_dbv(input_dbv, output_dbv),
        }
        self._emit_point(point, index)

    def _emit_point(self, point: dict, index: int):
        self._points.append(point)
        self.point_ready.emit(dict(point))
        self.progress.emit(round((index + 1) * 100 / len(self.config.frequencies_hz)))
        if index == 0:
            self.log.emit(
                f"{'Freq (Hz)':>12}\t"
                f"{f'VIN (dBV, INPUT{self.config.vin_input_channel})':>20}\t"
                f"{f'VOUT (dBV, INPUT{self.config.vout_input_channel})':>20}\t"
                f"{f'VIN DC (V, INPUT{self.config.vin_input_channel})':>22}\t"
                f"{f'VOUT DC (V, INPUT{self.config.vout_input_channel})':>22}\t"
                f"{'PSRR (dB)':>12}"
            )
        self.log.emit(
            f"{point['frequency_hz']:>12.6g}\t"
            f"{point['input_dbv']:>20.4f}\t"
            f"{point['output_dbv']:>20.4f}\t"
            f"{point['input_dc_v']:>22.6f}\t"
            f"{point['output_dc_v']:>22.6f}\t"
            f"{point['psrr_db']:>12.3f}"
        )

    def _cleanup_audio_precision(self, success: bool, message: str) -> tuple[bool, str]:
        ap = self.audio_precision
        if ap is None:
            return success, message
        if self._owns_audio_precision:
            try:
                ap.disconnect()
            except Exception:
                logger.error("Audio Precision 断开连接失败", exc_info=True)
                self.log.emit("[WARN] AP 断开连接失败")
        return success, message

    def _config_dict(self) -> dict:
        return {
            "measurement_method": "audio_precision",
            "ap_project_path": self.config.project_path,
            "ap_signal_path": self.config.signal_path,
            "ap_measurement": self.config.measurement,
            "ap_connection_mode": self.config.connection_mode,
            "ap_ssh_profile": self.config.ssh_profile,
            "ap_ssh_host": self.config.ssh_host,
            "ap_ssh_user": self.config.ssh_user,
            "ap_ssh_port": self.config.ssh_port,
            "ap_ssh_python": self.config.ssh_python,
            "ap_vin_input_channel": self.config.vin_input_channel,
            "ap_vout_input_channel": self.config.vout_input_channel,
            "ap_output_channel": self.config.output_channel,
            "ap_amplitude_mvrms": self.config.amplitude_vrms * 1000.0,
            "ap_offset_v": self.config.offset_v,
            "ap_fft_length": self.config.fft_length,
            "ap_fft_window": self.config.fft_window,
            "ap_fft_averages": self.config.fft_averages,
            "ap_bandwidth_hz": self.config.bandwidth_hz,
            "ap_start_frequency_hz": self.config.frequencies_hz[0],
            "ap_end_frequency_hz": self.config.frequencies_hz[-1],
            "ap_frequency_points": len(self.config.frequencies_hz),
            "ap_frequencies_hz": list(self.config.frequencies_hz),
            "ap_limit_db": self.config.limit_db,
        }
