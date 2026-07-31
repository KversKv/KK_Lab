#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KK LAB工具主入口
"""

import sys
import os
import logging
import warnings
import faulthandler

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

faulthandler.enable()
import pyvisa
from PySide6.QtWidgets import QApplication, QProxyStyle
from PySide6.QtCore import qInstallMessageHandler, QtMsgType, Qt
from PySide6.QtGui import QIcon
from log_config import setup_logging, get_logger
from debug_config import DEBUG_MOCK
from version import version_string
from ui.main_window import MainWindow
from ui.theme import configure_high_dpi

WITH_AI_ASSISTANT = os.environ.get("KK_LAB_WITH_AI", "1").strip().lower() not in (
    "0",
    "false",
    "off",
    "no",
)

setup_logging(level=logging.INFO)
if WITH_AI_ASSISTANT:
    from core.ai.log_ring import install_log_ring

    install_log_ring()


logger = get_logger(__name__)


def _global_excepthook(exc_type, exc_value, exc_tb):
    if exc_type is KeyboardInterrupt:
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))


sys.excepthook = _global_excepthook

warnings.filterwarnings("ignore", module=r"pyvisa_py\.tcpip")

_original_rm_del = pyvisa.ResourceManager.__del__

def _safe_rm_del(self):
    try:
        _original_rm_del(self)
    except Exception:
        pass

pyvisa.ResourceManager.__del__ = _safe_rm_del

class HoverFixStyle(QProxyStyle):
    def __init__(self, base_style=None):
        super().__init__(base_style)



    def polish(self, obj):
        super().polish(obj)
        from PySide6.QtWidgets import QWidget
        if isinstance(obj, QWidget):
            obj.setAttribute(Qt.WA_Hover, True)


def custom_message_handler(msg_type, context, message):
    if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
        return
    logger.debug("%s:%s - %s", context.file, context.line, message)


def main():
    """主函数"""
    logger.info("%s starting", version_string())
    logger.debug("Application starting")
    qInstallMessageHandler(custom_message_handler)

    # 高 DPI 取整策略（须在 QApplication 创建前设置；Qt6 默认即 PassThrough，显式声明）
    configure_high_dpi()
    app = QApplication(sys.argv)
    app.setStyle(HoverFixStyle("Fusion"))
    # QToolTip 是顶级窗口，不继承 MainWindow 的 palette；Fusion 下会回落系统默认
    # （Windows 深色模式为黑底），需显式 QSS 保证深底浅字可读。
    app.setStyleSheet("""
        QToolTip {
            background-color: #282c30;
            color: #d7dce2;
            border: 1px solid #4a5568;
            padding: 4px 6px;
        }
    """)
    
    _base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    _icon_path = os.path.join(_base, "resources", "icons", "kk_lab.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))
        logger.debug("Application icon loaded: %s", _icon_path)
    
    logger.debug("DEBUG_MOCK=%s", DEBUG_MOCK)
    logger.info("WITH_AI_ASSISTANT=%s", WITH_AI_ASSISTANT)
    main_window = MainWindow(with_ai=WITH_AI_ASSISTANT)
    main_window.show()
    logger.debug("MainWindow shown, entering event loop")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
