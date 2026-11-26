# -*- coding: utf-8 -*-
"""临时冒烟：示波器页 set_compact_mode 四按钮 reparent / 还原。"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

app = QApplication([])

from ui.pages.oscilloscope.oscilloscope_base_ui import OscilloscopeBaseUI

page = OscilloscopeBaseUI()
page.resize(1200, 800)
page.show()
app.processEvents()

hdr = page._capture_header_layout
act = page._trigger_action_layout
assert hdr.indexOf(page.capture_btn) == 3, hdr.indexOf(page.capture_btn)
assert hdr.indexOf(page.invert_btn) == 4
assert act.indexOf(page.trigger_run_stop_btn) == 0
assert act.indexOf(page.trigger_single_btn) == 1

page.set_compact_mode(True)
app.processEvents()
for btn in (page.capture_btn, page.invert_btn, page.trigger_run_stop_btn, page.trigger_single_btn):
    assert btn.parentWidget() is page._compact_panel, btn
    assert not btn.isHidden(), btn
assert not page._compact_panel.isHidden()
for w in (page.visa_resource_combo, page.search_btn, page.connect_btn,
          page._left_splitter, page._right_settings_scroll, page._quick_function_card,
          page.title_label, page.instrument_info_label):
    assert w.isHidden(), w
hint = page.minimumSizeHint()
print("compact minimumSizeHint:", hint.width(), hint.height())
assert hint.height() < 120, hint

page.set_compact_mode(False)
app.processEvents()
assert hdr.indexOf(page.capture_btn) == 3
assert hdr.indexOf(page.invert_btn) == 4
assert act.indexOf(page.trigger_run_stop_btn) == 0
assert act.indexOf(page.trigger_single_btn) == 1
assert page._compact_panel.isHidden()
for w in (page.visa_resource_combo, page.search_btn, page.connect_btn,
          page._left_splitter, page._right_settings_scroll, page._quick_function_card,
          page.title_label, page.instrument_info_label):
    assert not w.isHidden(), w
assert page.capture_btn.parentWidget() is not page._compact_panel

# 幂等
page.set_compact_mode(False)
page.set_compact_mode(True)
page.set_compact_mode(True)
page.set_compact_mode(False)
app.processEvents()
assert hdr.indexOf(page.capture_btn) == 3

print("OSC COMPACT VIEW TEST PASS")
