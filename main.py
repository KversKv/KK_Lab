#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
功耗测试工具主入口
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import qInstallMessageHandler, QtMsgType
from ui.main_window import MainWindow

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
    
    # 创建主窗口
    main_window = MainWindow()
    main_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
