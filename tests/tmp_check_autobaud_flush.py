"""临时验证：Auto-Baud 扫描结束重启读线程前清空驱动 RX 缓冲（验证后删除）。"""
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
        self.init_serial_connection(mode=MODE_FULL, prefix="FlushTest")
        root = QVBoxLayout(self)
        self.complete_serialComWidget(root)

    def append_log(self, msg):
        pass


class FakeConn:
    is_open = True

    def __init__(self):
        self.calls = []

    def reset_input_buffer(self):
        self.calls.append("flush")


app = QApplication(sys.argv)
w = W()

fake = FakeConn()
w._serial_conn = fake
w._serial_connected = True
w._start_serial_read = lambda: fake.calls.append("read_start")

# 已连接：先 flush 再重启读线程
w._sc_on_auto_baud_thread_cleanup()
assert fake.calls == ["flush", "read_start"], fake.calls

# 未连接：不 flush 不重启
fake.calls.clear()
w._serial_connected = False
w._sc_on_auto_baud_thread_cleanup()
assert fake.calls == [], fake.calls

# 连接对象为 None：不崩溃
w._serial_connected = True
w._serial_conn = None
w._sc_on_auto_baud_thread_cleanup()
assert fake.calls == ["read_start"], fake.calls

print("ALL CHECKS PASSED")
sys.stdout.flush()
os._exit(0)  # 跳过 Qt offscreen 析构阶段（与断言无关）
