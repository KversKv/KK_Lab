#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功耗测试工具主入口
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
from ui.main_window import MainWindow

setup_logging(level=logging.DEBUG)
# setup_logging(level=logging.DEBUG)    # 全部输出
# setup_logging(level=logging.INFO)     # 默认 - 正常运行信息
# setup_logging(level=logging.WARNING)  # 仅警告和错误
# setup_logging(level=logging.ERROR)    # 仅错误
# import logging

# # 创建模块级 logger
# logger = logging.getLogger(__name__)

# # 使用标准级别
# logger.error("Failed to download dlog data.")     
# logger.info("Step 1: Setting Vbat to 3V...")        
# logger.debug(f"Downloaded {size} bytes of dlog.")   




logger = get_logger(__name__)

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
    logger.debug("Application starting")
    qInstallMessageHandler(custom_message_handler)
    
    app = QApplication(sys.argv)
    app.setStyle(HoverFixStyle("Fusion"))
    
    _base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    _icon_path = os.path.join(_base, "resources", "icons", "kk_lab.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))
        logger.debug("Application icon loaded: %s", _icon_path)
    
    logger.debug("DEBUG_MOCK=%s", DEBUG_MOCK)
    main_window = MainWindow()
    main_window.show()
    logger.debug("MainWindow shown, entering event loop")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
