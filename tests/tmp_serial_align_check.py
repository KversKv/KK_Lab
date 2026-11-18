import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication

app = QApplication([])

from ui.modules.serialCom_module.serial_log_panel import SerialLogPanel

panel = SerialLogPanel(show_timestamp=False)
line = "   6/     1034/DSP/I/M0    /   1 | mpu[OK]: addr=0x00B00000 valid=1 mem_attr=15 mem_type=24"
line2 = "  46/     5954/I/NONE  /   2 | CPU USAGE: busy=2 cpu_sleep=79 bus_sleep=0 subsys_sleep=19"
panel.append_log(f"[RX] {line}")
panel.append_log(f"[RX] {line2}")
panel.flush_pending()
text = panel.log_edit.toPlainText()
print(repr(text))
assert "   6/     1034/DSP/I/M0    /   1 |" in text, "alignment lost"
assert "  46/     5954/I/NONE  /   2 |" in text, "alignment lost (line2)"
assert panel.all_logs[0][0] == f"[RX] {line}", "raw changed"

# 关键词高亮（含空格关键词）仍应命中
panel.highlight_keywords.append({"keyword": "CPU USAGE", "bg": "#333300", "fg": "#ffff00"})
panel.rebuild_view()
text2 = panel.log_edit.toPlainText()
assert "  46/     5954/I/NONE  /   2 |" in text2, "alignment lost after rebuild"
html = panel.render_entry(panel.all_logs[1][1], 2)
assert "CPU&nbsp;USAGE</span>" in html, "keyword highlight broken"

# 过滤路径对齐
panel.filter_input.setText("mpu")
panel.apply_filter()
text3 = panel.log_edit.toPlainText()
assert "   6/     1034/DSP/I/M0    /   1 |" in text3, "alignment lost in filter view"

print("ALL PASS")
