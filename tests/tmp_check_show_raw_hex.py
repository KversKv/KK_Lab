"""临时验证：RX Config Show Raw HEX 开关（验证后删除）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PySide6.QtCore import Signal

from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin
from ui.modules.serialCom_module.serial_style import MODE_FULL


class W(SerialComMixin, QWidget):
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    def __init__(self):
        super().__init__()
        self.init_serial_connection(mode=MODE_FULL, prefix="RawHexTest")
        root = QVBoxLayout(self)
        self.complete_serialComWidget(root)

    def append_log(self, msg):
        pass


app = QApplication(sys.argv)
w = W()

BIN = b"hello\n\xbe\x19\x03\n"


def hex_lines(panel):
    return [raw for raw, _h, _n in panel.all_logs if "[RX(HEX)]" in raw]


# 1) 默认开启
assert w._sc_show_raw_hex_cb.isChecked()
assert w._sc_show_raw_hex is True
assert w._sc_log_panel.show_raw_hex is True

# 2) 组件路径（额外/浮窗）：开 -> 有 HEX 行；关 -> 无
comp = w._sc_log_panel
comp.clear_logs()
comp.append_rx_data(BIN)
assert hex_lines(comp), "HEX line missing when enabled"
comp.clear_logs()
comp.show_raw_hex = False
comp.append_rx_data(BIN)
assert not hex_lines(comp), "HEX line should be hidden when disabled"
assert any("[RX] hello" in raw for raw, _h, _n in comp.all_logs)
comp.show_raw_hex = True

# 3) 主面板路径：开 -> 有；勾选框关闭 -> 无且真值/组件跟随
w._sc_log_panel.clear_logs()
w._sc_on_data_received(BIN)
assert hex_lines(w._sc_log_panel), "primary HEX missing when enabled"
w._sc_show_raw_hex_cb.setChecked(False)
assert w._sc_show_raw_hex is False
assert w._sc_log_panel.show_raw_hex is False
w._sc_log_panel.clear_logs()
w._sc_on_data_received(BIN)
assert not hex_lines(w._sc_log_panel), "primary HEX should be hidden when disabled"
assert any("[RX] hello" in raw for raw, _h, _n in w._sc_log_panel.all_logs)

# 4) 新建额外面板继承当前值（关）
extra = w._build_extra_log_panel({"title": "T", "port": "COM1", "baudrate": 115200})
assert extra["frame"].show_raw_hex is False
w._sc_extra_log_panels.append(extra)
# 重新打开 -> 已存在额外面板跟随
w._sc_show_raw_hex_cb.setChecked(True)
assert extra["frame"].show_raw_hex is True
w._sc_extra_log_panels.remove(extra)
extra["frame"].deleteLater()

# 5) 持久化采集含新键
state = w._sc_collect_persisted_state()
assert state["ui"].get("show_raw_hex") is True, state["ui"].get("show_raw_hex")

print("ALL CHECKS PASSED")
sys.stdout.flush()
os._exit(0)  # 跳过 Qt offscreen 析构阶段（与断言无关）
