# -*- coding: utf-8 -*-
"""GPADC 指标卡显示逻辑验收（_ConfigAiMixin.update_test_result，offscreen Qt）。

验收 3：k_ideal/b_ideal 为 None 时卡片显示 Slope / Intercept，不出现 "Err"；
验收 7：有效点数 < 3 时所有 Force Voltage 卡片显示 "N/A"。
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from core.pmu_test.gpadc.gpadc_analysis import (
    compute_detailed_stats,
    compute_force_voltage_metrics,
)
from ui.pages.pmu_test.gpadc_test.mixins.config_ai_mixin import _ConfigAiMixin


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


_VALUE_ATTRS = (
    'inl_value', 'step_nl_value', 'sigma_noise_value', 'enob_value',
    'gain_error_value', 'offset_error_value', 'coverage_value',
    'avg_value', 'min_value', 'max_value', 'std_value', 'pp_value',
    'samples_value', 'raw_minmax_value', 'outliers_value', 'noise_free_value',
    'linearity_value',
)
_NAME_ATTRS = ('gain_name_label', 'offset_name_label', 'std_name_label',
               'inl_name_label')


class _CardsHarness(_ConfigAiMixin):
    """仅装配指标卡 QLabel 的最小宿主，复用真实显示逻辑。"""

    TEST_1000CNT = "1000CNT TEST"
    TEST_FORCE_VOLTAGE = "Force Voltage Test"

    def __init__(self):
        self.current_test_item = self.TEST_FORCE_VOLTAGE
        for attr in _VALUE_ATTRS + _NAME_ATTRS:
            setattr(self, attr, QLabel("---"))

    @staticmethod
    def _fmt_data_value(v):
        return str(int(v)) if float(v).is_integer() else f"{float(v):.2f}"


def _linear_params(**kwargs):
    v = [i * 0.1 for i in range(16)]
    m = [16228.0 * x + 15370.0 for x in v]
    s = [20.0] * len(v)
    n = [100] * len(v)
    return compute_force_voltage_metrics(v, m, std=s, n=n, **kwargs)


def test_none_mode_shows_slope_intercept_without_err(app):
    ui = _CardsHarness()
    params = _linear_params()
    assert params['ref_mode'] == 'none'
    ui.update_test_result(params)
    assert ui.gain_name_label.text() == "SLOPE"
    assert ui.offset_name_label.text() == "INTERCEPT"
    assert "LSB/V" in ui.gain_error_value.text()
    assert "LSB" in ui.offset_error_value.text()
    for attr in _VALUE_ATTRS + _NAME_ATTRS:
        assert "Err" not in getattr(ui, attr).text()


def test_spec_mode_titles_and_values(app):
    ui = _CardsHarness()
    params = _linear_params(k_ideal=16000.0, b_ideal=15000.0)
    ui.update_test_result(params)
    assert ui.gain_name_label.text() == "GAIN ERR"
    assert ui.offset_name_label.text() == "OFFSET ERR"
    assert "%" in ui.gain_error_value.text()
    assert "LSB" in ui.offset_error_value.text()


def test_batch_mode_titles(app):
    ui = _CardsHarness()
    history = [(16000.0, 15000.0), (16100.0, 15100.0), (16200.0, 15200.0)]
    params = _linear_params(ref_mode='batch_nominal', batch_history=history)
    ui.update_test_result(params)
    assert ui.gain_name_label.text() == "GAIN DEV vs BATCH"
    assert ui.offset_name_label.text() == "OFFSET DEV vs BATCH"


def test_invalid_points_show_na_on_all_fv_cards(app):
    ui = _CardsHarness()
    ui.update_test_result({'valid': False, 'points': 2})
    for attr in ('inl_value', 'step_nl_value', 'sigma_noise_value', 'enob_value',
                 'gain_error_value', 'offset_error_value', 'coverage_value'):
        assert getattr(ui, attr).text() == "N/A"


def test_inl_below_noise_floor_marks_yellow(app):
    ui = _CardsHarness()
    params = _linear_params()
    # 纯线性数据 INL=0，低于噪声底
    assert params['inl_below_noise']
    ui.update_test_result(params)
    assert ui.inl_value.objectName() == "metric_value_yellow"
    assert "noise floor" in ui.inl_value.toolTip()


def test_cnt_cards_full_mean_trimmed_tooltip_and_group_title(app):
    ui = _CardsHarness()
    ui.current_test_item = ui.TEST_1000CNT
    raw = [2840 + (i % 7) for i in range(1000)]
    stats = compute_detailed_stats(raw, raw_before_filter=raw + [65535],
                                   outliers_removed=1)
    stats['algo_divisor'] = 8
    ui.update_test_result(stats)
    assert "trimmed mean" in ui.avg_value.toolTip()
    assert ui.std_name_label.text() == "STD (code, avg of 8)"
    assert ui.outliers_value.text() == "1"
    assert "65535" in ui.raw_minmax_value.text()
    assert ui.noise_free_value.text() not in ("---", "N/A")
    # 未启用分组聚合时标题还原
    stats['algo_divisor'] = 1
    ui.update_test_result(stats)
    assert ui.std_name_label.text() == "STD (code)"