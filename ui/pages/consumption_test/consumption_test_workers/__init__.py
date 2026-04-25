#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Consumption Test 下的所有 Worker(QObject)集中管理。

历史上 consumption_test.py 里堆叠了六个 Worker 以及大量重复的 force-datalog
流程。本包把它们拆分为:
 - common.py             : 单位、格式化、datalog 任务流程片段
 - download_worker.py    : 固件下载 Worker
 - chip_check_worker.py  : BES chip check Worker
 - consumption_worker.py : 基础功耗测试 Worker
 - force_worker.py       : BaseForceTestWorker + ForceHigh + ForceAuto
 - auto_test_worker.py   : Auto Test Worker(自动多 BIN 流程)

同时保留带下划线前缀的别名(`_DownloadWorker` 等),以便主文件可直接沿用
原有的引用名称。
"""

from .common import (
    CURRENT_UNIT,
    _UNIT_CONFIG,
    _format_current_unified,
    format_current_short,
)
from .download_worker import DownloadWorker
from .chip_check_worker import ChipCheckWorker
from .consumption_worker import ConsumptionTestWorker
from .force_worker import (
    BaseForceTestWorker,
    ConsumptionTestForceHighWorker,
    ConsumptionTestForceWorker,
)
from .auto_test_worker import AutoTestWorker

# 向后兼容的旧名字(带下划线前缀)
_DownloadWorker = DownloadWorker
_ChipCheckWorker = ChipCheckWorker
_ConsumptionTestWorker = ConsumptionTestWorker
_ConsumptionTestForceHighWorker = ConsumptionTestForceHighWorker
_ConsumptionTestForceWorker = ConsumptionTestForceWorker
_AutoTestWorker = AutoTestWorker

__all__ = [
    "CURRENT_UNIT",
    "_UNIT_CONFIG",
    "_format_current_unified",
    "format_current_short",
    "DownloadWorker",
    "ChipCheckWorker",
    "ConsumptionTestWorker",
    "BaseForceTestWorker",
    "ConsumptionTestForceHighWorker",
    "ConsumptionTestForceWorker",
    "AutoTestWorker",
    "_DownloadWorker",
    "_ChipCheckWorker",
    "_ConsumptionTestWorker",
    "_ConsumptionTestForceHighWorker",
    "_ConsumptionTestForceWorker",
    "_AutoTestWorker",
]
