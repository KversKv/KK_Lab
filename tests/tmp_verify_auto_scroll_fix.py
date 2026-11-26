# 临时验证脚本：auto-scroll 误恢复修复（验证后可删）
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QWheelEvent

from ui.modules.serialCom_module.serial_log_panel import SerialLogPanel

app = QApplication(sys.argv)
panel = SerialLogPanel(max_lines=300)
panel.resize(600, 400)
panel.show()
app.processEvents()

sb = panel.log_edit.verticalScrollBar()

# 1) 填满缓冲并触发顶部裁行
for i in range(400):
    panel.append_log(f"[RX] line {i} " + "x" * 40)
panel.flush_pending()
panel.flush_pending()
app.processEvents()
assert sb.maximum() > 0, "scrollbar should have range"
assert panel.auto_scroll is True

# 2) 模拟用户滚轮向上 -> auto-scroll 应停用
panel._user_scroll_input_ts = time.monotonic()
sb.setValue(sb.maximum() // 2)
app.processEvents()
assert panel.auto_scroll is False, "user scroll up must disable auto-scroll"
assert not panel.scroll_lock_btn.isChecked()

# 3) 无用户输入时持续追加新日志（含裁行/钳位/延迟布局）-> auto-scroll 必须保持停用
for round_i in range(10):
    for i in range(100):
        panel.append_log(f"[RX] burst {round_i}-{i} " + "y" * 40)
    panel.flush_pending()
    app.processEvents()
    assert panel.auto_scroll is False, f"auto-scroll wrongly re-enabled at round {round_i}"
    assert not panel.scroll_lock_btn.isChecked()

# 4) 用户滚轮回到底部 -> auto-scroll 应恢复
panel._user_scroll_input_ts = time.monotonic()
sb.setValue(sb.maximum())
app.processEvents()
assert panel.auto_scroll is True, "user scroll to bottom must re-enable auto-scroll"
assert panel.scroll_lock_btn.isChecked()

# 5) 真实 Wheel 事件路径：eventFilter 应记录输入时间戳
panel._user_scroll_input_ts = 0.0
ev = QWheelEvent(QPoint(10, 10), panel.log_edit.viewport().mapToGlobal(QPoint(10, 10)),
                 QPoint(0, 0), QPoint(0, -120), Qt.NoButton, Qt.NoModifier,
                 Qt.NoScrollPhase, False)
app.sendEvent(panel.log_edit.viewport(), ev)
assert time.monotonic() - panel._user_scroll_input_ts < 1.0, "wheel event must mark user input"

print("ALL PASS")
