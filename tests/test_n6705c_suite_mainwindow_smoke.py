#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MainWindow 入口冒烟：N6705C 一级菜单 → suite 装载、tab 切换同步、compact 可见性。"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer


def main():
    app = QApplication(sys.argv)

    from ui.main_window import MainWindow
    win = MainWindow(with_ai=False)
    win.show()

    def _check():
        suite = win.n6705c_suite_ui
        assert suite is not None, "suite 未装载"
        assert suite.isVisible(), "suite 不可见"
        assert win.current_instrument_ui == "power_analyser", win.current_instrument_ui
        assert win.n6705c_analyser_ui is suite.analyser_page
        assert win.n6705c_datalog_ui is suite.datalog_page
        # 嵌入模式：非顶层、无窗口 flags
        assert not suite.isWindow(), "嵌入模式应为子部件"

        compact_btn = win.top_bar.compact_view_button
        assert compact_btn.isVisible(), "analyser tab 下 compact 按钮应可见"

        # 切到 datalog tab
        suite.switch_page("datalog")
        assert win.current_instrument_ui == "datalog", win.current_instrument_ui
        assert not compact_btn.isVisible(), "datalog tab 下 compact 按钮应隐藏"

        # 截图链：顶栏按钮 → _resolve_capture_page → datalog 子页
        page = win._resolve_capture_page()
        assert page is suite.datalog_page, type(page)

        # 切回 analyser
        suite.switch_page("analyser")
        assert win.current_instrument_ui == "power_analyser"
        assert compact_btn.isVisible()

        # 帮助 key 随动
        suite.switch_page("datalog")
        assert win._get_current_help_key() == "datalog", win._get_current_help_key()
        suite.switch_page("analyser")
        assert win._get_current_help_key() == "power_analyser", win._get_current_help_key()

        # nav 一级菜单：PA 按钮点击不再弹二级菜单（无 pa_submenu 属性）
        assert not hasattr(win.nav, "pa_submenu"), "二级菜单应已移除"
        win.nav.handle_nav_button_clicked(win.nav.n6705c_power_analyzer_btn)
        assert win.n6705c_suite_ui.isVisible()

        print("MAINWINDOW_SMOKE_OK")
        # 走正常关闭流程（closeEvent → connection_hub.shutdown 线程清理），
        # 直接 app.quit 会跳过清理导致 QThread 析构崩溃
        win.close()

    QTimer.singleShot(2000, _check)
    QTimer.singleShot(6000, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
