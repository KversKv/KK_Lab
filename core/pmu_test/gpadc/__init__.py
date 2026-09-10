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
from .gpadc_multi_temp import (
    parse_hw_int,
    parse_iic_command_text,
    run_multi_ch_temp_test,
    writes_to_command_text,
)

__all__ = [
    "compute_reg_stats",
    "compute_calibration",
    "compute_detailed_stats",
    "parse_uart_gpadc_raw",
    "ALGORITHM_REGISTRY",
    "apply_algorithm",
    "describe_algorithm",
    "TestWorker",
    "parse_hw_int",
    "parse_iic_command_text",
    "run_multi_ch_temp_test",
    "writes_to_command_text",
]
