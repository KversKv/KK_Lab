# -*- coding: utf-8 -*-
"""临时冒烟：MainWindow 最小视图按钮在示波器页的进入/退出/切页自动退出。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("KK_LAB_WITH_AI", "0")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

app = QApplication([])

from ui.main_window import MainWindow

mw = MainWindow(with_ai=False)
mw.show()
app.processEvents()

mw._create_oscilloscope_ui()
app.processEvents()
btn = mw.top_bar.compact_view_button
assert btn.isVisible(), "compact button should be visible on oscilloscope page"
page = mw.oscilloscope_ui

btn.setChecked(True)
app.processEvents()
assert mw._compact_view is True
assert page._compact_view_active is True
assert mw._compact_active_page is page


def phase2():
    assert mw.isFixedSize() if hasattr(mw, "isFixedSize") else True
    w, h = mw.width(), mw.height()
    print("compact window size:", w, h)
    assert h < 200, h
    # 切页自动退出：切到 thermal_chamber
    mw._create_thermal_chamber_ui()
    app.processEvents()
    assert not btn.isChecked(), "button should auto-uncheck on page switch"
    assert mw._compact_view is False
    assert page._compact_view_active is False
    assert page._capture_header_layout.indexOf(page.capture_btn) == 3
    print("MW OSC COMPACT TEST PASS")
    mw.close()
    app.quit()


QTimer.singleShot(200, phase2)
QTimer.singleShot(8000, lambda: (print("TIMEOUT FAIL"), app.exit(1)))
app.exec()
