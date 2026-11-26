# -*- coding: utf-8 -*-
"""临时验证：file_dialog_memory 记忆/重启恢复/失效回退 + 各改动模块可导入。"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ui.modules.serialCom_module import file_dialog_memory as fdm

tmp = tempfile.mkdtemp(prefix="fdm_test_")
store = os.path.join(tmp, "file_dialog_dirs.json")
fdm._storage_path = lambda: store

dir_a = os.path.join(tmp, "a")
os.makedirs(dir_a)

# 1) 记忆 + 读取
fdm.remember_dir("export_log", dir_a)
assert fdm.last_dir("export_log") == dir_a, "remember/last_dir failed"
assert fdm.initial_save_path("export_log", "x.txt") == os.path.join(dir_a, "x.txt")
assert os.path.isfile(store), "not persisted immediately"

# 2) 模拟重启（清内存缓存，重新从 JSON 加载）
fdm._loaded = False
fdm._dirs.clear()
assert fdm.last_dir("export_log") == dir_a, "restart restore failed"

# 3) remember_path 取 dirname
fdm.remember_path("qc_export", os.path.join(dir_a, "sub.json"))
assert fdm.last_dir("qc_export") == dir_a

# 4) 目录消失 → 回退默认
os.rmdir(dir_a)
assert fdm.last_dir("export_log", "DEFAULT") == "DEFAULT", "fallback failed"
assert fdm.initial_save_path("export_log", "x.txt") == "x.txt"
assert fdm.last_dir("never_used", "FB") == "FB"

# 5) 各改动模块可导入（含 Qt 组件/对话框/Mixin）
from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
import ui.modules.serialCom_module.serial_log_panel  # noqa: F401
import ui.modules.serialCom_module.dialogs.save_dialog  # noqa: F401
import ui.modules.serialCom_module.dialogs.settings_dialog  # noqa: F401
import ui.modules.serialCom_module.serial_chart_dialog  # noqa: F401
import ui.modules.serialCom_module.mixins.script_mixin  # noqa: F401
import ui.modules.serialCom_module.mixins.send_mixin  # noqa: F401
import ui.modules.serialCom_module.mixins.filter_save_mixin  # noqa: F401
import ui.modules.serialCom_module.independent_window  # noqa: F401
import ui.modules.serialCom_module.serialCom_module_frame  # noqa: F401

# 6) 集成：SerialLogPanel.export_logs 初始路径 = 记忆目录 + 默认文件名
from PySide6.QtWidgets import QFileDialog
from ui.modules.serialCom_module.serial_log_panel import SerialLogPanel

dir_b = os.path.join(tmp, "b")
os.makedirs(dir_b)
fdm.remember_dir("export_log", dir_b)
captured = {}

def _fake_save(parent, caption, directory, name_filter, *a, **k):
    captured["dir"] = directory
    return os.path.join(dir_b, "out.txt"), "Text Files (*.txt)"

_orig = QFileDialog.getSaveFileName
QFileDialog.getSaveFileName = staticmethod(_fake_save)
try:
    panel = SerialLogPanel(title="T")
    panel.export_logs()
finally:
    QFileDialog.getSaveFileName = _orig
assert captured["dir"].startswith(dir_b), f"export initial dir wrong: {captured}"
assert fdm.last_dir("export_log") == dir_b

print("ALL CHECKS PASSED")
