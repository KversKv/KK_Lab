#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""640 高度 left_nav 标题显示诊断：真实 GUI + 真实字体，截图 + 几何指标。"""

import os
import sys

os.environ["KK_LAB_WITH_AI"] = "0"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtCore import QTimer

app = QApplication(sys.argv)

from ui.main_window import MainWindow  # noqa: E402
from debug_config import DEBUG_MOCK  # noqa: E402

print(f"DEBUG_MOCK = {DEBUG_MOCK}")

win = MainWindow(with_ai=False)
win.show()
app.processEvents()

win.resize(966, 640)
app.processEvents()


def report(tag):
    nav = win.nav
    left_nav = win.left_nav
    scroll = nav.nav_scroll_area
    vp = scroll.viewport()
    content = scroll.widget()
    print(f"\n=== {tag} ===")
    print(f"window={win.width()}x{win.height()} density={nav._density} "
          f"left_nav h={left_nav.height()}")
    print(f"viewport h={vp.height()} content h={content.height()} "
          f"vscroll_max={scroll.verticalScrollBar().maximum()}")
    bottom = win.status_panel.help_btn.parentWidget()
    print(f"bottom h={bottom.height()} hint={bottom.sizeHint().height()} "
          f"rows={len(win.status_panel.instrument_status_items)}")
    for t in content.findChildren(QLabel):
        if t.objectName() != "navGroupTitle":
            continue
        cr = t.contentsRect()
        fh = t.fontMetrics().height()
        asc = t.fontMetrics().ascent()
        desc = t.fontMetrics().descent()
        pos = t.mapTo(vp, t.rect().topLeft())
        vis = 0 <= pos.y() and pos.y() + t.height() <= vp.height()
        cm = t.contentsMargins()
        print(f"{t.text():<15} h={t.height()} content_h={cr.height()} "
              f"font h={fh} asc={asc} desc={desc} y={pos.y()} vis={vis} "
              f"cm=({cm.left()},{cm.top()},{cm.right()},{cm.bottom()}) "
              f"margin={t.margin()} indent={t.indent()} "
              f"frameShape={t.frameShape()} minH={t.minimumHeight()} maxH={t.maximumHeight()}")


QTimer.singleShot(800, lambda: (
    report("966x640"),
    win.nav.nav_scroll_area.viewport().grab().save(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "nav_640_scroll.png")),
    win.left_nav.grab().save(
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "nav_640_leftnav.png")),
    print("screenshots saved"),
    win.close(),
    app.quit(),
))

app.exec()
