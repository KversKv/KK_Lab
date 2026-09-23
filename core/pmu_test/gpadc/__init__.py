# -*- coding: utf-8 -*-
"""GPADC 测试：analysis（纯函数）+ worker（仅 QtCore）。"""

from .gpadc_analysis import (
    compute_reg_stats,
    compute_calibration,
    compute_detailed_stats,
    parse_uart_gpadc_raw,
    parse_uart_gpadc_raw_volt,
    parse_raw_lsb_value,
    solve_ft_kb,
    assess_ft_errors,
    ALGORITHM_REGISTRY,
    apply_algorithm,
    describe_algorithm,
    assess_fluctuation,
    compare_algorithm_effect,
)
from .gpadc_worker import TestWorker
from .gpadc_ft_check import run_ft_calib_check
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
    "parse_uart_gpadc_raw_volt",
    "parse_raw_lsb_value",
    "solve_ft_kb",
    "assess_ft_errors",
    "ALGORITHM_REGISTRY",
    "apply_algorithm",
    "describe_algorithm",
    "assess_fluctuation",
    "compare_algorithm_effect",
    "TestWorker",
    "run_ft_calib_check",
    "parse_hw_int",
    "parse_iic_command_text",
    "run_multi_ch_temp_test",
    "writes_to_command_text",
]
