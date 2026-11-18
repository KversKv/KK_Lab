# 临时验证：Update Log 跨行选中 / 全选 / 复制（offscreen）
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor

app = QApplication(sys.argv)

from ui.modules.serialCom_module.dialogs.settings_dialog import _SerialSettingsDialog

dlg = _SerialSettingsDialog()
dlg.show()
app.processEvents()

view = dlg._update_log_view
assert view.isReadOnly()
assert view.textInteractionFlags() & Qt.TextSelectableByMouse

# 全选：跨多个日期卡片与条目（多行）
view.selectAll()
sel = view.textCursor().selectedText()
assert "2026-11-18" in sel and "2026-11-17" in sel, "select all must span dates"
assert "\u2029" in sel, "selection must be multi-line"
view.copy()
clip = QApplication.clipboard().text()
assert "2026-11-18" in clip and "2026-11-17" in clip
assert "\n" in clip, "copied text must contain line breaks"

# 跨行局部选中：从文档起点向下选 3 行
cur = view.textCursor()
cur.movePosition(QTextCursor.Start)
cur.movePosition(QTextCursor.Down, QTextCursor.KeepAnchor, 3)
view.setTextCursor(cur)
partial = cur.selectedText()
assert "\u2029" in partial, "partial selection must span lines"
view.copy()
clip_partial = QApplication.clipboard().text()
assert clip_partial and "\n" in clip_partial

# 语言切换后重渲染，仍支持全选复制（set_value 静默不 emit，须模拟真实点击）
from PySide6.QtTest import QTest

QTest.mouseClick(dlg.update_log_lang_toggle, Qt.LeftButton)
app.processEvents()
assert "设置新增 Update Log 标签页" in view.toPlainText()
view.selectAll()
view.copy()
clip_zh = QApplication.clipboard().text()
assert "设置新增 Update Log 标签页" in clip_zh and "\n" in clip_zh

dlg.close()
dlg.deleteLater()
app.processEvents()
print("ALL PASS")
