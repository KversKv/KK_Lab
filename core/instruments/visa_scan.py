# -*- coding: utf-8 -*-
"""通用 VISA 资源扫描（*IDN? 关键词过滤）。

UI 连接 Mixin 的 Search 按钮统一经本模块后台扫描，UI 层禁止直接 import pyvisa。
探测串行执行（IVI-VISA 并发 viOpen/viRead/viClose 会堆损坏崩溃 0xc0000374，
见 core/AGENTS.md 局部坑点），禁止改为线程池并发。
"""

import pyvisa
from PySide6.QtCore import QObject, Signal

from log_config import get_logger

logger = get_logger(__name__)


def discover_visa_by_idn(keywords, timeout_ms=2000):
    """枚举 VISA 资源并逐个 open + *IDN? 探测，返回 IDN 命中任一关键词的地址列表。

    keywords: 匹配子串列表（大小写不敏感），如 ("DSOX", "MSO")。
    串行探测（禁并发）；单点失败仅跳过该地址；ResourceManager 枚举失败抛异常。
    """
    upper_keywords = tuple(kw.upper() for kw in keywords)
    rm = None
    matched = []
    try:
        rm = pyvisa.ResourceManager()
        all_resources = list(rm.list_resources()) or []
        for dev in all_resources:
            instr = None
            try:
                instr = rm.open_resource(dev, timeout=timeout_ms)
                idn = instr.query("*IDN?").strip()
                if any(kw in idn.upper() for kw in upper_keywords):
                    matched.append(dev)
            except Exception:
                logger.debug("VISA probe skipped %s", dev, exc_info=True)
            finally:
                if instr is not None:
                    try:
                        instr.close()
                    except Exception:
                        pass
    finally:
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass
    return matched


class VisaIdnScanWorker(QObject):
    """后台 VISA 扫描 Worker（QObject + moveToThread 范式，仅 QtCore）。"""

    finished = Signal(list)
    error = Signal(str)

    def __init__(self, keywords, timeout_ms=2000, parent=None):
        super().__init__(parent)
        self._keywords = tuple(keywords)
        self._timeout_ms = timeout_ms

    def run(self):
        try:
            self.finished.emit(
                discover_visa_by_idn(self._keywords, self._timeout_ms)
            )
        except Exception as e:
            logger.debug("VISA scan failed", exc_info=True)
            self.error.emit(str(e))
            self.finished.emit([])
