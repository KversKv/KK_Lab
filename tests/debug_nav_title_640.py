#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""640 高度下 left_nav 分组标题显示诊断（offscreen，一次性）。"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["KK_LAB_WITH_AI"] = "0"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)

from ui.main_window import MainWindow  # noqa: E402
from debug_config import DEBUG_MOCK  # noqa: E402

print(f"DEBUG_MOCK = {DEBUG_MOCK}")

win = MainWindow(with_ai=False)
win.show()
win.resize(966, 640)
app.processEvents()

nav = win.nav
left_nav = win.left_nav
print(f"window={win.width()}x{win.height()} density={nav._density}")
print(f"left_nav h={left_nav.height()}")

scroll = nav.nav_scroll_area
vp = scroll.viewport()
content = scroll.widget()
print(f"scroll viewport h={vp.height()}  content h={content.height()}  "
      f"vscroll max={scroll.verticalScrollBar().maximum()}")

bottom = win.status_panel.help_btn.parentWidget()
print(f"bottom panel h={bottom.height()}  hint={bottom.sizeHint().height()}")
print(f"instrument rows={len(win.status_panel.instrument_status_items)}")

logo = left_nav.findChild(QLabel, "navLogo")
print(f"logo h={logo.height()}")

print("\n-- group titles --")
for t in content.findChildren(QLabel):
    if t.objectName() != "navGroupTitle":
        continue
    cr = t.contentsRect()
    fh = t.fontMetrics().height()
    # 标题相对 viewport 的可见性
    pos_in_vp = t.mapTo(vp, t.rect().topLeft())
    visible = 0 <= pos_in_vp.y() and pos_in_vp.y() + t.height() <= vp.height()
    print(f"{t.text():<15} h={t.height()} contentRect_h={cr.height()} "
          f"font_h={fh} y_in_vp={pos_in_vp.y()} fully_visible={visible}")

print("\n-- buttons --")
for b in nav._density_widgets:
    if b.objectName() == "navGroupTitle":
        continue
    pos_in_vp = b.mapTo(vp, b.rect().topLeft())
    visible = 0 <= pos_in_vp.y() and pos_in_vp.y() + b.height() <= vp.height()
    if not visible:
        print(f"{b.title_label.text():<18} h={b.height()} y_in_vp={pos_in_vp.y()} fully_visible={visible}")
print("(仅列出不可见按钮；无输出=全部可见)")

win.close()
