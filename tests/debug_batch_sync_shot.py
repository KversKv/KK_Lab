#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Quick Setup 同步态截图：建组 {2,3,4} 后 grab Quick Setup 面板。"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from PySide6.QtWidgets import QApplication

from instruments.mock.mock_instruments import MockN6705C
from ui.pages.power_analyzer.power_analyzer_analyser_ui import N6705CAnalyserUI

app = QApplication.instance() or QApplication([])
page = N6705CAnalyserUI()
mock = MockN6705C()
page.devices["A"]["n6705c"] = mock
page.devices["A"]["is_connected"] = True
page._rebuild_dynamic_sections()

page._toggle_batch_sync("A", 1, 2, True)
page._toggle_batch_sync("A", 3, 4, True)
page.batch_voltage_inputs["A"][0].setText("3.3000")
page.batch_voltage_inputs["A"][2].setText("1.2000")

page.resize(700, page.sizeHint().height())
page.show()
app.processEvents()

out = os.path.join(os.path.dirname(__file__), "_batch_sync_shot.png")
page.batch_tools_panel.grab().save(out)
print("saved:", out)
page.deleteLater()
