# -*- coding: utf-8 -*-
"""SerialCom 模块 BUG 修复（B1-B18）冒烟测试：offscreen 实例化 + 关键路径断言。

运行：.venv\\Scripts\\python.exe tests\\test_serialcom_fixes.py
"""
import json
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import Signal

from ui.modules.serialCom_module.serialCom_module_frame import (
    SerialComMixin, MODE_FULL,
)
from ui.modules.serialCom_module.serialCom_module_frame import add_serial_port_item
from ui.modules.serialCom_module.independent_window import _IndependentSerialWindow
from ui.modules.serialCom_module.dialogs.script_dialogs import _SerialScriptEditorDialog
from core.serial_io.read_worker import SerialReadWorker

PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail and not cond else ""))


class W(SerialComMixin, QWidget):
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)


def make_widget(cfg_dir):
    w = W()
    w._sc_user_config_dir = lambda: cfg_dir  # 隔离持久化目录
    w.init_serial_connection(mode=MODE_FULL, prefix="T")
    lay = QVBoxLayout(w)
    w.complete_serialComWidget(lay)
    return w


def main():
    app = QApplication([])
    tmp = tempfile.mkdtemp(prefix="sc_test_")

    w = make_widget(tmp)

    # --- B5: baud editable 切换后 editingFinished 重绑到新 lineEdit ---
    w._sc_auto_detect_cb.setChecked(False)
    le1 = w._sc_baud_combo.lineEdit()
    check("B5 editable 后 lineEdit 存在", le1 is not None)
    check("B5 lineEdit 已绑定", getattr(w, "_sc_baud_line_edit_bound", None) is le1)
    w._sc_auto_detect_cb.setChecked(True)
    w._sc_auto_detect_cb.setChecked(False)
    le2 = w._sc_baud_combo.lineEdit()
    check("B5 反复切换后 lineEdit 为新对象且重绑", le2 is not None and le2 is not le1
          and getattr(w, "_sc_baud_line_edit_bound", None) is le2)
    # Custom 占位项不报错、不改真值
    old_baud = w._serial_baudrate
    w._sc_baud_combo.setCurrentText("Custom")
    w._sc_on_baudrate_changed()
    check("B5 Custom 占位项静默忽略", w._serial_baudrate == old_baud)
    w._sc_baud_combo.setCurrentText("115200")

    # --- B6: 端口精确匹配（COM3 不误判 COM30） ---
    w._sc_port_combo.clear()
    add_serial_port_item(w._sc_port_combo, "COM30 - USB Serial")
    add_serial_port_item(w._sc_port_combo, "COM3 - USB Serial")
    w._sc_port_combo.setCurrentIndex(0)
    w._sc_last_port = "COM3"
    w._sc_try_restore_last_port()
    check("B6 COM3 精确恢复", w._sc_port_combo.currentText() == "COM3",
          f"got {w._sc_port_combo.currentText()}")

    # --- B3: 侧栏 Show Time 同步主面板组件 ---
    w._sc_on_show_time_toggled(False)
    check("B3 组件 show_timestamp 同步", w._sc_log_panel.show_timestamp is False)
    w._sc_on_show_time_toggled(True)

    # --- B8+B15: 断开停脚本 + 清行缓冲 ---
    w._sc_rx_line_buf = "half-line"
    w._sc_script_running = True
    w._sc_do_disconnect()
    check("B8 断开停止脚本", w._sc_script_running is False)
    check("B15 断开清空行缓冲", w._sc_rx_line_buf == "")

    # --- B16: 额外面板空端口 Connect 有报错日志 ---
    panel = w._build_extra_log_panel({"title": "P1", "port": "", "baudrate": 115200})
    w._sc_extra_log_panels.append(panel)
    w._sc_extra_panel_connect(panel)
    raws = [r for r, _h, _n in panel["frame"].all_logs]
    check("B16 空端口报错日志", any("No valid port" in r for r in raws), str(raws))

    # --- B9: session_id 用稳定 uid，失败重连不累积 session ---
    panel["config"]["port"] = "CNCOM_NONE_X"
    w._sc_extra_panel_connect(panel)  # 失败，但 session_id 已赋值
    sid1 = panel.get("session_id")
    n1 = len(w._sc_session_manager.sessions)
    w._sc_extra_panel_connect(panel)  # 再次失败：应先清旧 session
    sid2 = panel.get("session_id")
    n2 = len(w._sc_session_manager.sessions)
    check("B9 session_id 稳定(uid)", sid1 == sid2 and sid1.startswith("extra_"), f"{sid1} vs {sid2}")
    check("B9 失败重连 session 不累积", n2 <= n1, f"n1={n1} n2={n2}")

    # --- B1: 聚焦主面板但 primary session 不存在时 manager active 清空，发送不错板 ---
    mgr = w._sc_session_manager
    es = mgr.create_session(session_id="extra_fake", display_name="F", auto_activate=False)
    es._connected = True  # 模拟额外面板已连接
    mgr.set_active_session("extra_fake")
    w._sc_active_log_panel_index = 1
    w._sc_on_primary_panel_clicked()
    check("B1 manager active 已清空", mgr.active_session_id is None, str(mgr.active_session_id))
    check("B1 主面板发送不错板", w._sc_primary_send(b"x") is False)

    # --- B2: 脚本发送锁定主面板 ---
    calls = []
    orig = w._sc_primary_send
    w._sc_primary_send = lambda d: calls.append(d) or True
    w._sc_active_log_panel_index = 1  # 焦点在额外面板
    w._sc_script_send_step({"cmd": "AT", "send_type": "text"})
    w._sc_active_log_panel_index = 0
    w._sc_primary_send = orig
    check("B2 脚本发送走主面板", calls == [b"AT\r\n"], str(calls))

    # --- B7: read worker finished 信号（异常/关闭后线程可退出） ---
    class _FakeConn:
        is_open = False
        in_waiting = 0
    fired = []
    worker = SerialReadWorker(_FakeConn())
    worker.finished.connect(lambda: fired.append(1))
    worker.run()
    check("B7 read worker 结束发 finished", fired == [1])

    # --- B12: 脚本编辑器保留步骤级 send_type/line_ending ---
    dlg = _SerialScriptEditorDialog(
        parent=w,
        script={"name": "s", "steps": [
            {"cmd": "AA55", "priority": 1, "wait_ms": 10, "wait_keyword": "",
             "wait_timeout_ms": 0, "send_type": "hex", "line_ending": ""},
        ]},
        quick_commands=[],
    )
    steps = dlg._collect_steps()
    check("B12 扩展键保留", steps[0].get("send_type") == "hex" and "line_ending" in steps[0],
          str(steps))
    dlg.deleteLater()

    # --- 浮窗：读线程装配（error/finished 已连接）+ 空端口报错 ---
    win = _IndependentSerialWindow({"title": "F", "port": "", "baudrate": 115200}, parent=None)
    win._do_connect()
    win_raws = [r for r, _h, _n in win._panel.all_logs]
    check("浮窗空端口报错", any("No port configured" in r for r in win_raws), str(win_raws))
    win.close()

    # --- B4: 持久化回放（show_timestamp/sidebar/show_send/line_ending） ---
    state = w._sc_collect_persisted_state()
    state["ui"]["show_timestamp"] = False
    state["ui"]["sidebar_visible"] = False
    state["ui"]["show_send"] = False
    state["ui"]["line_ending"] = "\n"
    with open(w._sc_persisted_path(), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)

    w2 = make_widget(tmp)
    check("B4 show_timestamp 属性回放", w2._sc_show_timestamp is False)
    check("B4 组件 show_timestamp 回放同步", w2._sc_log_panel.show_timestamp is False)
    check("B4 Show Time 勾选态回放", w2._sc_rx_show_time_cb.isChecked() is False)
    check("B4 sidebar 按钮态回放", w2._sc_sidebar_toggle_btn.isChecked() is False)
    check("B4 sidebar 属性回放", w2._sc_sidebar_visible is False)
    check("B4 Show Send 勾选态回放", w2._sc_show_send_cb.isChecked() is False)
    le_idx = w2._sc_ending_combo.currentIndex()
    check("B4 Line Ending 回放", (w2._sc_ending_combo.itemData(le_idx) or "") == "\n",
          f"idx={le_idx}")

    # --- B17: 未连接时即时应用为空操作（不崩） ---
    w2._sc_apply_serial_cfg_to_live_connection()
    check("B17 未连接空操作", True)

    app.processEvents()

    # 清理：停 hotplug 监控与读写线程，避免解释器退出时 QThread 销毁崩溃
    try:
        w2.close_serial()
        w.close_serial()
        from ui.modules.serialCom_module.serial_hotplug import SerialPortHotplugMonitor
        SerialPortHotplugMonitor.instance().stop()
    except Exception:
        pass
    app.processEvents()

    print(f"\n==== {len(PASS)} passed, {len(FAIL)} failed ====")
    if FAIL:
        print("FAILED:", FAIL)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
