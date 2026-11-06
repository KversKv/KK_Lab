# -*- coding: utf-8 -*-
"""PSRR 纯算法与配置校验，不依赖 Qt。"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable


_FREQUENCY_RE = re.compile(
    r"^((?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([kKmM]?)\s*(?:[hH][zZ])?$"
)


@dataclass(frozen=True)
class PSRRConfig:
    source_channel: int = 1
    input_channel: int = 1
    output_channel: int = 2
    dc_voltage: float = 5.0
    afg_amplitude_mvpp: float = 100.0
    frequencies_hz: tuple[float, ...] = (100.0, 1000.0, 10000.0, 100000.0)
    cycles: float = 5.0
    output_scale_mv: float = 10.0
    limit_db: float = 0.0
    close_channel_after: bool = False

    @property
    def afg_amplitude_vpp(self) -> float:
        return self.afg_amplitude_mvpp / 1000.0

    @property
    def nominal_input_vrms(self) -> float:
        return self.afg_amplitude_vpp / (2.0 * math.sqrt(2.0))

    def validate(self) -> None:
        for name, channel in (
            ("Source", self.source_channel),
            ("Input", self.input_channel),
            ("Output", self.output_channel),
        ):
            if channel not in (1, 2, 3, 4):
                raise ValueError(f"{name} channel 必须为 1~4")
        if self.input_channel == self.output_channel:
            raise ValueError("输入与输出示波器通道不能相同")
        if self.dc_voltage <= 0:
            raise ValueError("DC Voltage 必须大于 0 V")
        if self.afg_amplitude_mvpp <= 0:
            raise ValueError("AFG Amplitude 必须大于 0 mVpp")
        if self.afg_amplitude_vpp / 2.0 >= self.dc_voltage:
            raise ValueError("AFG 正弦峰值不能超过 DC Voltage，避免电源输出过零")
        if not self.frequencies_hz:
            raise ValueError("至少配置一个扫频点")
        if any(not math.isfinite(f) or f <= 0 for f in self.frequencies_hz):
            raise ValueError("频率必须为大于 0 的有限数值")
        if self.cycles < 1:
            raise ValueError("Capture Cycles 不能小于 1")
        if self.output_scale_mv <= 0:
            raise ValueError("Output Scale 必须大于 0 mV/div")


@dataclass(frozen=True)
class AudioPrecisionPSRRConfig:
    project_path: str = ""
    signal_path: str = "Signal Path1"
    measurement: str = "PSRR"
    frequencies_hz: tuple[float, ...] = (100.0, 1000.0, 10000.0, 100000.0)
    limit_db: float = 0.0

    def validate(self) -> None:
        if not self.signal_path.strip():
            raise ValueError("Audio Precision Signal Path 不能为空")
        if not self.measurement.strip():
            raise ValueError("Audio Precision Measurement 不能为空")
        if not self.frequencies_hz:
            raise ValueError("至少配置一个扫频点")
        if any(not math.isfinite(f) or f <= 0 for f in self.frequencies_hz):
            raise ValueError("频率必须为大于 0 的有限数值")


def parse_frequency_points(text: str | Iterable[float]) -> tuple[float, ...]:
    """解析逗号/分号/空白分隔频点，支持 k/M 与 Hz 后缀，去重并升序。"""
    if not isinstance(text, str):
        values = tuple(float(value) for value in text)
    else:
        tokens = [token for token in re.split(r"[,，;；\s]+", text.strip()) if token]
        values_list = []
        for token in tokens:
            match = _FREQUENCY_RE.fullmatch(token)
            if match is None:
                raise ValueError(f"无法识别频率：{token}")
            value = float(match.group(1))
            suffix = match.group(2).lower()
            if suffix == "k":
                value *= 1e3
            elif suffix == "m":
                value *= 1e6
            values_list.append(value)
        values = tuple(values_list)
    if not values:
        raise ValueError("至少输入一个频率点")
    if any(not math.isfinite(value) or value <= 0 for value in values):
        raise ValueError("频率必须为大于 0 的有限数值")
    return tuple(sorted(set(values)))


def generate_frequency_points(start_hz: float, end_hz: float, points: int) -> tuple[float, ...]:
    """生成包含起止点的对数等间隔频点。"""
    if not math.isfinite(start_hz) or start_hz <= 0:
        raise ValueError("Start Frequency 必须为大于 0 的有限数值")
    if not math.isfinite(end_hz) or end_hz <= start_hz:
        raise ValueError("End Frequency 必须大于 Start Frequency")
    if points < 2:
        raise ValueError("Points 不能小于 2")
    ratio = end_hz / start_hz
    values = tuple(
        start_hz * ratio ** (index / (points - 1)) for index in range(points)
    )
    return values[:-1] + (float(end_hz),)


def config_from_dict(data: dict) -> PSRRConfig:
    if "frequencies_hz" in data:
        frequencies = data["frequencies_hz"]
    else:
        frequencies = generate_frequency_points(
            float(data.get("start_frequency_hz", 100.0)),
            float(data.get("end_frequency_hz", 100000.0)),
            int(data.get("frequency_points", 4)),
        )
    if "afg_amplitude_mvpp" in data:
        amplitude_mvpp = float(data["afg_amplitude_mvpp"])
    elif "ripple_mv_rms" in data:
        amplitude_mvpp = float(data["ripple_mv_rms"]) * 2.0 * math.sqrt(2.0)
    else:
        amplitude_mvpp = 100.0
    config = PSRRConfig(
        source_channel=int(data.get("source_channel", 1)),
        input_channel=int(data.get("input_channel", 1)),
        output_channel=int(data.get("output_channel", 2)),
        dc_voltage=float(data.get("dc_voltage", 5.0)),
        afg_amplitude_mvpp=amplitude_mvpp,
        frequencies_hz=parse_frequency_points(frequencies),
        cycles=float(data.get("cycles", 5.0)),
        output_scale_mv=float(data.get("output_scale_mv", 10.0)),
        limit_db=float(data.get("limit_db", 0.0)),
        close_channel_after=bool(data.get("close_channel_after", False)),
    )
    config.validate()
    return config


def audio_precision_config_from_dict(data: dict) -> AudioPrecisionPSRRConfig:
    config = AudioPrecisionPSRRConfig(
        project_path=str(data.get("ap_project_path", "")).strip(),
        signal_path=str(data.get("ap_signal_path", "Signal Path1")).strip(),
        measurement=str(data.get("ap_measurement", "PSRR")).strip(),
        frequencies_hz=parse_frequency_points(data["ap_frequencies_hz"])
        if "ap_frequencies_hz" in data else generate_frequency_points(
            float(data.get("ap_start_frequency_hz", 100.0)),
            float(data.get("ap_end_frequency_hz", 100000.0)),
            int(data.get("ap_frequency_points", 4)),
        ),
        limit_db=float(data.get("ap_limit_db", 0.0)),
    )
    config.validate()
    return config


def calculate_psrr_db(input_vrms: float, output_vrms: float) -> float:
    """PSRR = 20 log10(Vin_ripple / Vout_ripple)。"""
    if not math.isfinite(input_vrms) or input_vrms <= 0:
        raise ValueError("输入纹波必须为大于 0 的有限数值")
    if not math.isfinite(output_vrms) or output_vrms <= 0:
        raise ValueError("输出纹波必须为大于 0 的有限数值")
    return 20.0 * math.log10(input_vrms / output_vrms)


def scope_timebase_seconds(frequency_hz: float, cycles: float) -> float:
    if frequency_hz <= 0 or cycles <= 0:
        raise ValueError("频率和捕获周期数必须大于 0")
    return cycles / frequency_hz / 10.0


def acquisition_settle_seconds(timebase_s: float) -> float:
    """DSOX 重捕获等待：16×时基，按项目约定设置双下限。"""
    lower_bound = 2.5 if timebase_s > 10e-3 else 1.0
    return max(lower_bound, 16.0 * timebase_s)


def simulate_psrr_point(frequency_hz: float, input_vrms: float) -> dict:
    """可重复的 Mock 曲线，仅用于界面与流程验证。"""
    psrr_db = (
        70.0
        - 20.0 * math.log10(1.0 + frequency_hz / 1000.0)
        + 4.0 * math.exp(-math.log10(max(frequency_hz, 1.0) / 100.0) ** 2)
    )
    output_vrms = input_vrms / (10.0 ** (psrr_db / 20.0))
    return {
        "frequency_hz": float(frequency_hz),
        "input_vrms": float(input_vrms),
        "output_vrms": float(output_vrms),
        "psrr_db": float(psrr_db),
    }


def summarize_results(points: list[dict], limit_db: float = 0.0) -> dict:
    if not points:
        return {
            "point_count": 0,
            "min_psrr_db": None,
            "max_psrr_db": None,
            "average_psrr_db": None,
            "passed": None,
        }
    values = [float(point["psrr_db"]) for point in points]
    minimum = min(values)
    return {
        "point_count": len(points),
        "min_psrr_db": minimum,
        "max_psrr_db": max(values),
        "average_psrr_db": sum(values) / len(values),
        "min_frequency_hz": float(points[values.index(minimum)]["frequency_hz"]),
        "passed": minimum >= float(limit_db),
    }
