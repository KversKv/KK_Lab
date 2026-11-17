# -*- coding: utf-8 -*-
"""临时冒烟：ASCII 模式二进制段以 [RX(HEX)] 独立行显示（验证后删除）。"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import Signal

from ui.modules.serialCom_module.serialCom_module_frame import SerialComMixin, MODE_FULL


class W(SerialComMixin, QWidget):
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)


app = QApplication([])
tmp = tempfile.mkdtemp(prefix="sc_rxhex_")
w = W()
w._sc_user_config_dir = lambda: tmp
w.init_serial_connection(mode=MODE_FULL, prefix="T")
lay = QVBoxLayout(w)
w.complete_serialComWidget(lay)

hs = bytes.fromhex("BE1903000001D4")
assert not w._sc_rx_display_hex  # ASCII 模式
w._sc_rx_auto_flush_cb.setChecked(False)  # 关闭 Auto Flush 仍须可见

w._sc_on_data_received(hs)
w._sc_on_data_received(b"BOOT OK\r\n" + hs + b"TEMP=25.3\r\n")
w._sc_on_data_received(b"PARTIAL=" + hs)  # 半行文本 + 二进制：先刷文本保时序
w._sc_on_data_received("电压=3.3V\r\n".encode("utf-8"))
w._sc_log_panel.flush_pending()
text = w._sc_log_panel.log_edit.toPlainText()
print("---- main panel ----")
print(text)
assert "[RX(HEX)] BE 19 03 00 00 01 D4" in text, "handshake HEX line missing"
assert "\\x" not in text, "inline escapes still present"
assert "[RX] BOOT OK" in text and "[RX] TEMP=25.3" in text
assert "[RX] PARTIAL=" in text and "[RX] 电压=3.3V" in text
assert text.index("[RX] PARTIAL=") < text.index("[RX(HEX)] BE 19", text.index("[RX] PARTIAL="))
assert w._sc_rx_line_buf == "", f"line buf not empty: {w._sc_rx_line_buf!r}"

# 帧内含可打印字节 0x50='P'：不得劈成 HEX/文本/HEX 多段
hs_p = bytes.fromhex("BE500003000001ED")
w._sc_on_data_received(hs_p)
w._sc_on_data_received(bytes.fromhex("BE500103000001EC"))
w._sc_log_panel.flush_pending()
text2 = w._sc_log_panel.log_edit.toPlainText()
print("---- printable-hole frames ----")
print(text2)
assert "[RX(HEX)] BE 50 00 03 00 00 01 ED" in text2, "frame with 0x50 split"
assert "[RX(HEX)] BE 50 01 03 00 00 01 EC" in text2
assert not any(l.rstrip().endswith("[RX] P") for l in text2.splitlines()), "stray printable-hole text line"
assert not any(l.rstrip().endswith("[RX(HEX)] BE") for l in text2.splitlines())

# 额外面板/浮窗共用组件路径
from ui.modules.serialCom_module.serial_log_panel import SerialLogPanel

p = SerialLogPanel(status_bar="rxtx")
p.append_rx_data(b"BOOT OK\r\n" + hs + b"TEMP=25.3\r\n")
p.append_rx_data(hs_p)
p.flush_pending()
ptext = p.log_edit.toPlainText()
print("---- shared panel ----")
print(ptext)
assert "[RX(HEX)] BE 19 03 00 00 01 D4" in ptext
assert "[RX(HEX)] BE 50 00 03 00 00 01 ED" in ptext
assert "[RX] BOOT OK" in ptext and "[RX] TEMP=25.3" in ptext
assert not any(l.rstrip().endswith("[RX] P") for l in ptext.splitlines())

print("SMOKE PASS")
sys.stdout.flush()
w.close_serial()
os._exit(0)
