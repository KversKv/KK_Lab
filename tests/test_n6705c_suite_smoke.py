#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""N6705CSuiteWindow 冒烟：建窗 → 切换两页 → 自动关闭。"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from ui.pages.n6705c_power_analyzer.n6705c_suite_ui import (
    N6705CSuiteWindow, N6705CTop,
)


def main():
    app = QApplication(sys.argv)

    from core.instruments import InstrumentManager
    manager = InstrumentManager()
    top = N6705CTop()
    top.set_instrument_manager(manager)

    w = N6705CSuiteWindow(n6705c_top=top, instrument_manager=manager)
    w.setWindowTitle("N6705C Suite")
    w.resize(1440, 900)
    w.show()

    assert w.current_page_key() == "analyser", w.current_page_key()

    def _check():
        w.switch_page("datalog")
        assert w.current_page_key() == "datalog"
        w.switch_page("analyser")
        assert w.current_page_key() == "analyser"
        print("SMOKE_OK")

    QTimer.singleShot(1500, _check)
    QTimer.singleShot(3000, app.quit)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
