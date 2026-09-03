# -*- coding: utf-8 -*-
"""GPADC 测试：analysis（纯函数）+ worker（仅 QtCore）。"""

from .gpadc_analysis import (
    compute_reg_stats,
    compute_calibration,
    compute_detailed_stats,
    parse_uart_gpadc_raw,
    ALGORITHM_REGISTRY,
    apply_algorithm,
    describe_algorithm,
)
from .gpadc_worker import TestWorker

__all__ = [
    "compute_reg_stats",
    "compute_calibration",
    "compute_detailed_stats",
    "parse_uart_gpadc_raw",
    "ALGORITHM_REGISTRY",
    "apply_algorithm",
    "describe_algorithm",
    "TestWorker",
]
