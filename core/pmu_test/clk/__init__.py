# -*- coding: utf-8 -*-
"""CLK 测试：analysis（纯函数）+ worker（仅 QtCore）。"""

from .clk_analysis import (
    simulate_frequency,
    float_range,
    parse_tek_csv,
    parse_dslogic_csv,
    parse_generic_csv,
    find_sigrok_cli,
    analyze_clk_perf,
)
from .clk_worker import ClkTestWorker

__all__ = [
    "simulate_frequency",
    "float_range",
    "parse_tek_csv",
    "parse_dslogic_csv",
    "parse_generic_csv",
    "find_sigrok_cli",
    "analyze_clk_perf",
    "ClkTestWorker",
]
