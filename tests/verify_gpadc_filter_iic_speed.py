#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPADC 页新增功能冒烟验证（offscreen + DEBUG_MOCK，无需仪器）：
    1. Data Acquisition 的 IIC Speed 选择：默认值、配置导出/回填、
       _ensure_device_i2c 同步 speed_mode
    2. Outlier Filter：开关联动 spin 可用性、core filter_mean_deviation 语义、
       _apply_outlier_filter 剔除/全剔除回退、配置导出/回填
    3. FT Calibration Check 切换时 Algorithm/Outlier Filter 区隐藏

用法:
    python tests/verify_gpadc_filter_iic_speed.py
"""

import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import debug_config  # noqa: E402

debug_config.DEBUG_MOCK = True

from PySide6.QtWidgets import QApplication  # noqa: E402

from core.pmu_test.gpadc import filter_mean_deviation  # noqa: E402
from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode  # noqa: E402

logger = logging.getLogger("verify_gpadc_filter_iic_speed")


class _LogStub:
    def __init__(self):
        self.lines = []

    def emit(self, msg):
        self.lines.append(msg)


class _WorkerStub:
    def __init__(self):
        self.log = _LogStub()


def _check(name, cond):
    if not cond:
        raise AssertionError(name)
    logger.info("PASS: %s", name)


def _clear_config_memory():
    """清除页面 ConfigMemory 持久化文件，避免历史配置干扰默认值断言（测试前后各调一次）。"""
    from ui.resource_path import get_user_data_dir
    cfg_path = Path(get_user_data_dir("page_configs")) / "pmu_test" / "gpadc.json"
    if cfg_path.is_file():
        cfg_path.unlink()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    app = QApplication.instance() or QApplication([])

    from ui.pages.pmu_test.gpadc_test_ui import GPADCTestUI

    _clear_config_memory()
    page = GPADCTestUI()
    page._test_worker = _WorkerStub()

    # ---- core 纯函数语义 ----
    kept, removed = filter_mean_deviation([100, 102, 98, 130, 70], 5.0, 5.0)
    _check("core 非对称剔除: 剔除 +30/-30 两点", kept == [100, 102, 98] and removed == [130, 70])
    kept, removed = filter_mean_deviation([100, 100, 100, 130], 50.0, 50.0)
    _check("core 双阈值放宽: 全部保留", kept == [100, 100, 100, 130] and removed == [])
    kept, removed = filter_mean_deviation([100, 100, 100, 130], 50.0, 5.0)
    _check("core 非对称: 正向(+22.5)保留、负向(-7.5)剔除", kept == [130] and removed == [100, 100, 100])
    kept, removed = filter_mean_deviation([100, 200], 1.0, 1.0)
    _check("core 全剔除: kept 为空且 removed 为全部样本", kept == [] and removed == [100, 200])

    # ---- IIC Speed 控件 ----
    _check("IIC Speed 默认 100 kHz",
           page.iic_speed_combo.currentData() == int(I2CSpeedMode.SPEED_100K))
    page.iic_speed_combo.setCurrentIndex(2)
    cfg = page.get_test_config()
    _check("配置导出 iic_speed=400K", cfg['iic_speed'] == int(I2CSpeedMode.SPEED_400K))
    ok, msg = page.apply_config_to_controls({'iic_speed': int(I2CSpeedMode.SPEED_20K)}, silent=True)
    _check(f"配置回填 iic_speed=20K ({msg})",
           ok and page.iic_speed_combo.currentData() == int(I2CSpeedMode.SPEED_20K))

    # _ensure_device_i2c 同步 speed_mode（I2CInterface 创建不开设备，安全）
    page._iic_speed_snapshot = I2CSpeedMode.SPEED_750K
    dev = page._ensure_device_i2c()
    _check("_ensure_device_i2c 同步 speed_mode", dev.speed_mode == I2CSpeedMode.SPEED_750K)

    # ---- Outlier Filter 控件 ----
    _check("开关默认 OFF 且 spin 禁用",
           not page.outlier_filter_switch.isChecked()
           and not page.outlier_pos_offset.isEnabled()
           and not page.outlier_neg_offset.isEnabled())
    page.outlier_filter_switch.setChecked(True)
    _check("开关 ON 联动 spin 启用",
           page.outlier_pos_offset.isEnabled() and page.outlier_neg_offset.isEnabled())

    # _set_ui_enabled 不得越过开关状态
    page.outlier_filter_switch.setChecked(False)
    page._set_ui_enabled(True)
    _check("_set_ui_enabled(True) 后 spin 仍随开关禁用",
           not page.outlier_pos_offset.isEnabled())

    # 配置导出/回填
    page.outlier_filter_switch.setChecked(True)
    page.outlier_pos_offset.setValue(25.0)
    page.outlier_neg_offset.setValue(15.0)
    cfg = page.get_test_config()['outlier_filter']
    _check("配置导出 outlier_filter",
           cfg == {'enabled': True, 'pos_offset': 25.0, 'neg_offset': 15.0})
    ok, msg = page.apply_config_to_controls(
        {'outlier_filter': {'enabled': False, 'pos_offset': 5.0, 'neg_offset': 8.0}},
        silent=True)
    _check(f"配置回填 outlier_filter ({msg})",
           ok and not page.outlier_filter_switch.isChecked()
           and page.outlier_pos_offset.value() == 5.0
           and page.outlier_neg_offset.value() == 8.0
           and not page.outlier_pos_offset.isEnabled())

    # ---- _apply_outlier_filter 行为 ----
    page._outlier_filter_snapshot = None
    data = [100, 102, 98, 130]
    _check("未启用: 原样返回", page._apply_outlier_filter(list(data)) == data)

    page._outlier_filter_snapshot = {'pos': 5.0, 'neg': 5.0}
    page._test_worker = _WorkerStub()
    out = page._apply_outlier_filter([100, 100, 100, 100, 120])
    _check("启用: 剔除 +16 离群点（mean=104）", out == [100, 100, 100, 100])
    _check("启用: 输出 [FILTER] 日志",
           any("[FILTER]" in line for line in page._test_worker.log.lines))
    _check("启用: 日志打印被剔除值 120",
           any(line.strip() == "120" for line in page._test_worker.log.lines))

    page._test_worker = _WorkerStub()
    out = page._apply_outlier_filter([100, 200])
    _check("全剔除: 回退原始数据", out == [100, 200])
    _check("全剔除: 输出 [WARN] 日志",
           any("[WARN]" in line for line in page._test_worker.log.lines))
    _check("全剔除: 日志打印被剔除值 100,200",
           any(line.strip() == "100,200" for line in page._test_worker.log.lines))

    # ---- FT 测试项隐藏两区（offscreen 下 isVisible 恒 False，用 isHidden 判定） ----
    ft_idx = page.test_item_combo.findData(page.TEST_FT_CALIB_CHECK)
    page.test_item_combo.setCurrentIndex(ft_idx)
    _check("FT 项: Algorithm/Outlier Filter 区隐藏",
           page.algorithm_combo.isHidden()
           and page.outlier_filter_frame.isHidden())
    page.test_item_combo.setCurrentIndex(0)
    _check("切回 1000CNT: Outlier Filter 区恢复可见",
           not page.outlier_filter_frame.isHidden())

    logger.info("全部冒烟检查通过")
    _clear_config_memory()
    return 0


if __name__ == "__main__":
    sys.exit(main())
