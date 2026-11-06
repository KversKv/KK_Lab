# -*- coding: utf-8 -*-
"""PSRR 扫频 Worker，仅依赖 QtCore。"""
from __future__ import annotations

import math
import time

from PySide6.QtCore import QObject, Signal, Slot

from log_config import get_logger
from .psrr_analysis import (
    AudioPrecisionPSRRConfig,
    PSRRConfig,
    acquisition_settle_seconds,
    audio_precision_config_from_dict,
    calculate_psrr_db,
    config_from_dict,
    scope_timebase_seconds,
    simulate_psrr_point,
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
        self.log.emit(
            f"[DATA] Freq={point['frequency_hz']:g} Hz | "
            f"Vin={point['input_vrms'] * 1000:.4f} mVrms | "
            f"Vout={point['output_vrms'] * 1000:.4f} mVrms | "
            f"PSRR={point['psrr_db']:.3f} dB"
        )


class AudioPrecisionPSRRWorker(QObject):
    progress = Signal(int)
    point_ready = Signal(object)
    result_ready = Signal(object)
    log = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, config: dict | AudioPrecisionPSRRConfig,
                 audio_precision=None, parent=None):
        super().__init__(parent)
        self.config = (
            config if isinstance(config, AudioPrecisionPSRRConfig)
            else audio_precision_config_from_dict(config)
        )
        self.config.validate()
        self.audio_precision = audio_precision
        self._abort = False

    def stop(self):
        self._abort = True

    @Slot()
    def start(self):
        self.log.emit(
            f"[INFO] Audio Precision framework: project={self.config.project_path or '<current>'}, "
            f"signal path={self.config.signal_path}, measurement={self.config.measurement}, "
            f"points={len(self.config.frequencies_hz)}"
        )
        message = "Audio Precision PSRR 测量适配器尚未接入，框架已预留"
        self.log.emit(f"[WARN] {message}")
        self.progress.emit(0)
        self.finished.emit(False, message)
