# -*- coding: utf-8 -*-
"""PSRR 测试：纯算法与后台扫频 Worker。"""

from .psrr_analysis import (
    AudioPrecisionPSRRConfig,
    PSRRConfig,
    acquisition_settle_seconds,
    audio_precision_config_from_dict,
    calculate_psrr_db,
    calculate_psrr_from_dbv,
    config_from_dict,
    generate_frequency_points,
    parse_frequency_points,
    scope_timebase_seconds,
    select_audio_precision_bandwidth,
    simulate_psrr_point,
    spectrum_level_at_frequency,
    summarize_results,
)
from .psrr_worker import AudioPrecisionPSRRWorker, PSRRTestWorker

__all__ = [
    "AudioPrecisionPSRRConfig",
    "AudioPrecisionPSRRWorker",
    "PSRRConfig",
    "PSRRTestWorker",
    "acquisition_settle_seconds",
    "audio_precision_config_from_dict",
    "calculate_psrr_db",
    "calculate_psrr_from_dbv",
    "config_from_dict",
    "generate_frequency_points",
    "parse_frequency_points",
    "scope_timebase_seconds",
    "select_audio_precision_bandwidth",
    "simulate_psrr_point",
    "spectrum_level_at_frequency",
    "summarize_results",
]
