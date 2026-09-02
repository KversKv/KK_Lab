#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""冒烟：紧凑视图（最小视图）切换功能。

复现用户真实场景：从 main.py 启动 MainWindow（默认首页即 N6705C，不显式
切页）→ 验证按钮可见 → 触发紧凑视图 → 断言高度自适应（夹在内容
minimumHint 与 sizeHint 间，无底部空白）/ 页面区块可见性 / 导航隐藏 →
退出紧凑 → 断言还原 → 紧凑态下程序切页（datalog）→ 断言自动退出紧凑
并还原全窗口。
运行：python tests/diag_compact_view.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow, _COMPACT_VIEW_SIZE

FAILURES = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not cond:
        FAILURES.append(name)


def check_full_view(win):
    page = win.n6705c_analyser_ui
    check("页面完整：top_bar", page.top_bar.isVisible())
    check("页面完整：channel 区", page.channel_interaction_frame.isVisible())
    check("页面完整：Quick Setup", page.batch_tools_panel.isVisible())
    check("页面完整：consumption 区", page.consumption_test_panel.isVisible())
    check("左导航可见", win.left_nav.isVisible())


def check_compact_view(win):
    page = win.n6705c_analyser_ui
    btn = win.top_bar.compact_view_button
    check("按钮选中", btn.isChecked())
    # 自适应后：高度夹在内容 minimumHint 与 sizeHint 之间（无底部空白、无裁剪）
    min_h = win.minimumSizeHint().height()
    hint_h = win.sizeHint().height()
    print(f"  [尺寸] h={win.height()} minHint_h={min_h} sizeHint_h={hint_h} "
          f"w={win.width()}")
    check("高度自适应（≥内容需求，≤推荐尺寸）", min_h <= win.height() <= hint_h + 2,
          f"实际 h={win.height()} 夹区间 [{min_h}, {hint_h}]")
    check("宽度保持紧凑下限（双设备列不压缩）", win.width() >= _COMPACT_VIEW_SIZE[0],
          f"实际 w={win.width()}")
    check("页面仅 Quick Setup：top_bar 隐藏", not page.top_bar.isVisible())
    check("页面仅 Quick Setup：channel 区隐藏", not page.channel_interaction_frame.isVisible())
    check("页面仅 Quick Setup：Quick Setup 可见", page.batch_tools_panel.isVisible())
    check("Quick Setup 展开态", not page.batch_collapsed)
    check("页面仅 Quick Setup：consumption 区隐藏", not page.consumption_test_panel.isVisible())
    check("左导航隐藏", not win.left_nav.isVisible())


def run(win):
    page = win.n6705c_analyser_ui
    btn = win.top_bar.compact_view_button
    geo_before = win.geometry()

    print("=== 初始（N6705C Analyser 页，全窗口视图） ===")
    check("按钮可见", btn.isVisible())
    check("按钮未选中", not btn.isChecked())
    check_full_view(win)
    print(f"  窗口 geometry: {geo_before}")

    print("=== 触发紧凑视图 ===")
    btn.setChecked(True)

    def after_in():
        check_compact_view(win)

        print("=== 退出紧凑视图 ===")
        btn.setChecked(False)

        def after_out():
            check("窗口还原 geometry", win.geometry() == geo_before,
                  f"实际 {win.geometry()} vs 期望 {geo_before}")
            check_full_view(win)
            check("按钮未选中", not btn.isChecked())

            print("=== 紧凑态下程序切页（datalog）===")
            btn.setChecked(True)

            def after_in2():
                check_compact_view(win)
                win._switch_pa_mode("datalog")

                def after_away():
                    check("切离后按钮隐藏", not btn.isVisible())
                    check("切离后自动退出紧凑态", not win._compact_view)
                    check("切离后窗口恢复全窗口尺寸", win.geometry() == geo_before,
                          f"实际 {win.geometry()} vs 期望 {geo_before}")
                    check("切离后左导航还原", win.left_nav.isVisible())
                    # 切回 analyser 验证页面区块已随紧凑退出同步还原
                    win._switch_pa_mode("analyser")

                    def after_back():
                        check_full_view(win)
                        print(f"\n结果: {'全部通过' if not FAILURES else '失败项 ' + str(FAILURES)}")
                        QApplication.instance().quit()

                    QTimer.singleShot(150, after_back)

                QTimer.singleShot(150, after_away)

            QTimer.singleShot(150, after_in2)

        QTimer.singleShot(150, after_out)

    QTimer.singleShot(150, after_in)


def main():
    app = QApplication(sys.argv)
    win = MainWindow(with_ai=False)
    win.show()
    # 不显式切页：默认首页即 N6705C Analyser（复现 main.py 真实场景）
    QTimer.singleShot(1500, lambda: run(win))
    app.exec()
    sys.exit(1 if FAILURES else 0)


if __name__ == "__main__":
    main()
