# 临时复现脚本：到顶后新日志是否导致视图滚动（验证后可删）
import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint

from ui.modules.serialCom_module.serial_log_panel import SerialLogPanel

app = QApplication(sys.argv)
panel = SerialLogPanel(max_lines=300)
panel.resize(600, 400)
panel.show()
app.processEvents()

sb = panel.log_edit.verticalScrollBar()


def first_visible():
    return panel.log_edit.cursorForPosition(QPoint(0, 0)).block().text()[:60]


def pump(ms):
    end = time.monotonic() + ms / 1000.0
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)


for i in range(400):
    panel.append_log(f"[RX] line {i:05d} " + "x" * 40)
panel.flush_pending()
panel.flush_pending()
pump(100)
print(f"filled: value={sb.value()} max={sb.maximum()} auto={panel.auto_scroll}")

# 模拟用户滚轮滚到中间位置, 观察锚定是否稳定
panel._user_scroll_input_ts = time.monotonic()
sb.setValue(sb.maximum() // 2)
pump(50)
print(f"user->mid: value={sb.value()} auto={panel.auto_scroll} first={first_visible()!r}")
mid_anchor = first_visible()
for r in range(4):
    for i in range(60):
        panel.append_log(f"[RX] mid {r}-{i:03d} " + "z" * 40)
    panel.flush_pending()
    pump(120)
    print(f"mid round {r}: value={sb.value()} max={sb.maximum()} auto={panel.auto_scroll} "
          f"first={first_visible()!r}")
    assert first_visible() == mid_anchor, f"mid view drifted at round {r}"
    assert panel.auto_scroll is False

# 模拟用户滚轮滚到最顶
panel._user_scroll_input_ts = time.monotonic()
sb.setValue(0)
pump(50)
print(f"user->top: value={sb.value()} auto={panel.auto_scroll} first={first_visible()!r}")
top_anchor = first_visible()

for r in range(8):
    for i in range(60):
        panel.append_log(f"[RX] burst {r}-{i:03d} " + "y" * 40)
    panel.flush_pending()
    pump(120)  # 模拟 100ms 批量刷新间隔, 让延迟布局/事件跑完
    print(f"round {r}: value={sb.value()} max={sb.maximum()} auto={panel.auto_scroll} "
          f"btn={panel.scroll_lock_btn.isChecked()} first={first_visible()!r}")
    assert first_visible() == top_anchor, f"top view drifted at round {r}"
    assert panel.auto_scroll is False and not panel.scroll_lock_btn.isChecked()

# 恢复 Auto-scroll: 上限回到 max_lines, 文档裁回 max_lines 行, 视图回底
panel._user_scroll_input_ts = time.monotonic()
sb.setValue(sb.maximum())
pump(50)
for i in range(60):
    panel.append_log(f"[RX] resume {i:03d} " + "w" * 40)
panel.flush_pending()
pump(120)
print(f"resume: auto={panel.auto_scroll} cap={panel.log_edit.document().maximumBlockCount()} "
      f"blocks={panel.log_edit.document().blockCount()} value={sb.value()} max={sb.maximum()}")
assert panel.auto_scroll is True
assert panel.log_edit.document().maximumBlockCount() == panel.max_lines
assert panel.log_edit.document().blockCount() <= panel.max_lines
assert sb.value() >= sb.maximum() - 5
print("ALL PASS")
