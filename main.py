#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功耗测试工具主入口
"""

import sys
import os
import warnings
import pyvisa
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from PySide6.QtGui import QIcon
from ui.main_window import MainWindow

warnings.filterwarnings("ignore", module=r"pyvisa_py\.tcpip")

_original_rm_del = pyvisa.ResourceManager.__del__

def _safe_rm_del(self):
    try:
        _original_rm_del(self)
    except Exception:
        pass

pyvisa.ResourceManager.__del__ = _safe_rm_del

# 自定义消息处理器，过滤掉QPainter警告
def custom_message_handler(msg_type, context, message):
    # 过滤掉QPainter::end警告
    if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
        return
    # 其他消息正常输出
    print(f"{context.file}:{context.line} - {message}")


def main():
    """主函数"""
    # 安装自定义消息处理器
    qInstallMessageHandler(custom_message_handler)
    
    app = QApplication(sys.argv)
    # 设置应用样式
    app.setStyle("Fusion")
    
    # 设置应用图标（任务栏和窗口标题栏）
    _base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    _icon_path = os.path.join(_base, "resources", "icons", "kk_lab.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))
    
    # 创建主窗口
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

