#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MainWindow 内嵌 Module Test 页布局诊断：量取左栏滚动区/中栏几何并截图。

用法：python tests/diag_module_test_in_mainwindow.py
"""

import os
import sys

os.environ["KK_LAB_WITH_AI"] = "0"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication  # noqa: E402
from PySide6.QtCore import QTimer  # noqa: E402

app = QApplication(sys.argv)

from ui.main_window import MainWindow  # noqa: E402

win = MainWindow(with_ai=False)
win.show()
app.processEvents()

win._create_module_test_ui("ldo")
app.processEvents()

OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def report(tag):
    sub = win.module_test_ui.ldo_test_ui
    scroll = sub.left_scroll
    rail = sub.left_rail
    vp = scroll.viewport()
    vbar = scroll.verticalScrollBar()
    print(f"\n=== {tag} ===", flush=True)
    print(f"window={win.width()}x{win.height()}", flush=True)
    print(f"module_test_ui: w={win.module_test_ui.width()} h={win.module_test_ui.height()}", flush=True)
    print(f"left_scroll: w={scroll.width()} h={scroll.height()} minW={scroll.minimumWidth()} maxW={scroll.maximumWidth()}", flush=True)
    print(f"viewport: w={vp.width()} h={vp.height()}", flush=True)
    print(f"left_rail: w={rail.width()} h={rail.height()} hintW={rail.sizeHint().width()} hintH={rail.sizeHint().height()}", flush=True)
    print(f"vbar: visible={vbar.isVisible()} max={vbar.maximum()} w={vbar.width()}", flush=True)
    print(f"run_bar: pos=({sub.run_bar.x()},{sub.run_bar.y()}) w={sub.run_bar.width()} h={sub.run_bar.height()}", flush=True)
    print(f"subpage: w={sub.width()} h={sub.height()}", flush=True)
    win.grab().save(os.path.join(OUT_DIR, f"mt_main_{tag}.png"))
    print(f"saved mt_main_{tag}.png", flush=True)


STEPS = [(1600, 900), (1440, 810), (1280, 720)]
state = {"i": 0}


def step():
    i = state["i"]
    if i >= len(STEPS):
        win.close()
        app.quit()
        return
    w, h = STEPS[i]
    win.resize(w, h)
    app.processEvents()
    QTimer.singleShot(400, lambda: (report(f"{w}x{h}"), next_step()))


def next_step():
    state["i"] += 1
    step()


QTimer.singleShot(600, step)
app.exec()
