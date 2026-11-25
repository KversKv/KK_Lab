"""临时验证：主面板右键菜单（验证后删除）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMenu, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal

from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin
from ui.modules.serialCom_module.serial_style import MODE_FULL


class W(SerialComMixin, QWidget):
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    def __init__(self):
        super().__init__()
        self.init_serial_connection(mode=MODE_FULL, prefix="MenuTest")
        root = QVBoxLayout(self)
        self.complete_serialComWidget(root)

    def append_log(self, msg):
        pass


app = QApplication(sys.argv)
w = W()

# 1) 主面板本体已启用 CustomContextMenu
assert w._sc_log_panel.contextMenuPolicy() == Qt.CustomContextMenu, "panel body policy missing"

# 2) 未连接：Connect + Settings
menu = QMenu(w)
w._sc_primary_panel_menu_extra(menu)
texts = [a.text() for a in menu.actions() if not a.isSeparator()]
assert texts == ["Connect", "Settings..."], texts

# 3) 已连接：Disconnect + Settings
w._serial_connected = True
menu2 = QMenu(w)
w._sc_primary_panel_menu_extra(menu2)
texts2 = [a.text() for a in menu2.actions() if not a.isSeparator()]
assert texts2 == ["Disconnect", "Settings..."], texts2
w._serial_connected = False

# 4) 共用本体菜单构建器存在且额外面板路径可用（不 exec，仅填充）
assert callable(w._sc_panel_body_context_menu)
assert callable(w._sc_primary_panel_context_menu)
assert callable(w._sc_extra_panel_context_menu)

# 5) 改名真值链路仍在
assert w._sc_primary_panel_title == "Serial Log"
assert callable(w._sc_primary_panel_settings)

w.close_serial()
print("ALL CHECKS PASSED")
sys.stdout.flush()
os._exit(0)  # 跳过 Qt offscreen 析构阶段（与断言无关）
