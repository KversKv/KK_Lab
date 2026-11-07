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
    measurement: str = "Signal Analyzer"
    connection_mode: str = "vm_ssh"
    ssh_profile: str = "testvm"
    ssh_host: str = "192.168.208.128"
    ssh_user: str = "administrator"
    ssh_port: int = 22
    ssh_python: str = "py -3.12"
    vin_input_channel: int = 1
    vout_input_channel: int = 2
    output_channel: int = 1
    amplitude_vrms: float = 0.1
    offset_v: float = 3.8
    frequencies_hz: tuple[float, ...] = (100.0, 1000.0, 10000.0, 100000.0)
    limit_db: float = 0.0

    @property
    def bandwidth_hz(self) -> float:
        return select_audio_precision_bandwidth(max(self.frequencies_hz))

    def validate(self) -> None:
        if not self.signal_path.strip():
            raise ValueError("Audio Precision Signal Path 不能为空")
        if not self.measurement.strip():
            raise ValueError("Audio Precision Measurement 不能为空")
        if self.connection_mode not in ("local", "vm_ssh"):
            raise ValueError("Audio Precision Connection 必须为 local 或 vm_ssh")
        if self.connection_mode == "vm_ssh":
            if not self.ssh_profile.strip() and not self.ssh_host.strip():
                raise ValueError("SSH Profile 与 Guest IP 至少填写一项")
            if not 1 <= self.ssh_port <= 65535:
                raise ValueError("SSH Port 必须位于 1-65535")
            if not self.ssh_python.strip():
                raise ValueError("Guest Python Command 不能为空")
        for name, channel in (
            ("VIN", self.vin_input_channel),
            ("VOUT", self.vout_input_channel),
        ):
            if channel not in (1, 2):
                raise ValueError(f"Audio Precision {name} INPUT Channel 必须为 1 或 2")
        if self.vin_input_channel == self.vout_input_channel:
            raise ValueError("Audio Precision VIN 与 VOUT INPUT Channel 不能相同")
        if self.output_channel not in (1, 2):
            raise ValueError("Audio Precision Output Channel 必须为 1 或 2")
        if not math.isfinite(self.amplitude_vrms) or self.amplitude_vrms <= 0:
            raise ValueError("Audio Precision Output Amplitude 必须大于 0 Vrms")
        if not math.isfinite(self.offset_v) or self.offset_v <= 0:
            raise ValueError("Audio Precision DC Offset 必须大于 0 V")
        if self.amplitude_vrms * math.sqrt(2.0) >= self.offset_v:
            raise ValueError("正弦峰值不能超过 DC Offset，避免输出过零")
        if not self.frequencies_hz:
            raise ValueError("至少配置一个扫频点")
        if any(not math.isfinite(f) or f <= 0 for f in self.frequencies_hz):
            raise ValueError("频率必须为大于 0 的有限数值")
        select_audio_precision_bandwidth(max(self.frequencies_hz))


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


def generate_frequency_points(
    start_hz: float, end_hz: float, points: int, *, include_endpoints: bool = True
) -> tuple[float, ...]:
    """生成对数等间隔频点，可选择是否包含起止点。"""
    if not math.isfinite(start_hz) or start_hz <= 0:
        raise ValueError("Start Frequency 必须为大于 0 的有限数值")
    if not math.isfinite(end_hz) or end_hz <= start_hz:
        raise ValueError("End Frequency 必须大于 Start Frequency")
    if points < 2:
        raise ValueError("Points 不能小于 2")
    ratio = end_hz / start_hz
    if not include_endpoints:
        return tuple(
            start_hz * ratio ** (index / (points + 1))
            for index in range(1, points + 1)
        )
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
            include_endpoints=bool(data.get("include_endpoints", True)),
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
        measurement=str(data.get("ap_measurement", "Signal Analyzer")).strip(),
        connection_mode=str(data.get("ap_connection_mode", "vm_ssh")).strip(),
        ssh_profile=str(data.get("ap_ssh_profile", "testvm")).strip(),
        ssh_host=str(data.get("ap_ssh_host", "192.168.208.128")).strip(),
        ssh_user=str(data.get("ap_ssh_user", "administrator")).strip(),
        ssh_port=int(data.get("ap_ssh_port", 22)),
        ssh_python=str(data.get("ap_ssh_python", "py -3.12")).strip(),
        vin_input_channel=int(data.get("ap_vin_input_channel", 1)),
        vout_input_channel=int(data.get("ap_vout_input_channel", 2)),
        output_channel=int(data.get("ap_output_channel", 1)),
        amplitude_vrms=float(data.get("ap_amplitude_mvrms", 100.0)) / 1000.0,
        offset_v=float(data.get("ap_offset_v", 3.8)),
        frequencies_hz=parse_frequency_points(data["ap_frequencies_hz"])
        if "ap_frequencies_hz" in data else generate_frequency_points(
            float(data.get("ap_start_frequency_hz", 100.0)),
            float(data.get("ap_end_frequency_hz", 100000.0)),
            int(data.get("ap_frequency_points", 4)),
            include_endpoints=bool(data.get("ap_include_endpoints", True)),
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


def select_audio_precision_bandwidth(max_frequency_hz: float) -> float:
    """选择覆盖最高测试频率的 AP 模拟输入带宽档位。"""
    for bandwidth in (20000.0, 40000.0, 80000.0, 250000.0, 500000.0, 1000000.0):
        if max_frequency_hz <= bandwidth:
            return bandwidth
    raise ValueError("Audio Precision 最高测试频率不能超过 1 MHz")


def spectrum_level_at_frequency(
    frequencies_hz: Iterable[float], levels_dbv: Iterable[float], target_hz: float
) -> tuple[float, float]:
    """返回离目标频率最近的 FFT bin 频率与 dBV 电平。"""
    frequencies = tuple(float(value) for value in frequencies_hz)
    levels = tuple(float(value) for value in levels_dbv)
    if not frequencies or len(frequencies) != len(levels):
        raise ValueError("FFT 频率与电平数据为空或长度不一致")
    if any(not math.isfinite(value) or value < 0 for value in frequencies):
        raise ValueError("FFT 频率轴包含无效数值")
    first_positive_hz = next((value for value in frequencies if value > 0), None)
    if first_positive_hz is None:
        raise ValueError("FFT 频率轴不包含有效正频率")
    if target_hz < first_positive_hz or target_hz > frequencies[-1]:
        raise ValueError(f"目标频率 {target_hz:g} Hz 超出 FFT 频率范围")
    index = min(range(len(frequencies)), key=lambda i: abs(frequencies[i] - target_hz))
    level = levels[index]
    if not math.isfinite(level):
        raise ValueError(f"FFT {frequencies[index]:g} Hz 电平无效")
    return frequencies[index], level


def calculate_psrr_from_dbv(input_dbv: float, output_dbv: float) -> float:
    if not math.isfinite(input_dbv) or not math.isfinite(output_dbv):
        raise ValueError("FFT 输入/输出 dBV 电平必须为有限数值")
    return float(input_dbv - output_dbv)


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
