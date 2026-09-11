#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""侧栏 Serial/RX/TX Config 跟随聚焦面板回归。

覆盖：
1. 聚焦额外面板 -> 侧栏载入该面板 config（Serial + RX/TX），Auto-Detect/Auto Flush/System Log 禁用；
2. 侧栏控件修改即时写回绑定面板 config，不污染主面板 Mixin 属性 / _sc_primary_serial_cfg；
3. 切回主面板 -> 侧栏恢复主面板真值；
4. 面板 config 生效路径：rx_hex 数据渲染、show_send=False 不回显；
5. 聚焦额外面板时采集持久化，主面板 serial 段不串值。

可独立运行：
    python tests/test_serialcom_sidebar_follow.py
也可被 pytest 收集：
    pytest tests/test_serialcom_sidebar_follow.py
"""

import os
import sys
import traceback

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from PySide6.QtCore import Signal


def _ensure_app():
    return QApplication.instance() or QApplication([])


def _make_widget():
    import ui.modules.serialCom_module.serialCom_module_frame as frame
    import ui.modules.serialCom_module.mixins.log_panel_mixin as lpm
    import ui.modules.serialCom_module.mixins.connection_mixin as cm
    import ui.modules.serialCom_module.mixins.send_mixin as sm

    frame.DEBUG_MOCK = True
    lpm.DEBUG_MOCK = True
    cm.DEBUG_MOCK = True
    sm.DEBUG_MOCK = True

    from ui.modules.serialCom_module.serialCom_module_frame import MODE_FULL, SerialComMixin

    class _SmokeWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def append_log(self, msg):
            self._sc_append_system(msg, force_primary=True)

        def _sc_persisted_path(self):
            # 隔离持久化：指向不存在路径，避免本机配置污染测试
            return os.path.join(_ROOT, "tests", "_tmp_sidebar_cfg", "never_exist.json")

    app = _ensure_app()
    w = _SmokeWidget()
    w.init_serial_connection(mode=MODE_FULL, prefix="Sidebar")
    root = QVBoxLayout(w)
    w.complete_serialComWidget(root)
    w.resize(900, 500)
    w.show()
    app.processEvents()
    return app, w


def test_sidebar_follows_focus():
    app, w = _make_widget()

    # 主面板真值已初始化
    assert isinstance(getattr(w, "_sc_primary_serial_cfg", None), dict), "主面板 Serial 真值未初始化"
    assert w._sc_sidebar_bound_index == 0, "初始侧栏绑定应为主面板"

    panel_cfg = {
        "title": "P2", "port": "COM5", "baudrate": 57600,
        "databit": "7", "stopbit": "2", "parity": "Even", "flow": "RTS/CTS",
        "rx_hex": True, "show_timestamp": False,
        "tx_hex": True, "line_ending": "\n", "show_send": False,
    }
    panel = w._build_extra_log_panel(panel_cfg)
    w._sc_extra_log_panels.append(panel)
    w._sc_relayout_log_panels()

    # --- 聚焦额外面板：侧栏载入面板 config ---
    w._sc_on_log_panel_clicked(panel, None)
    app.processEvents()
    assert w._sc_sidebar_bound_index == 1, "侧栏未绑定到聚焦面板"
    assert w._sc_port_combo.currentText() == "COM5", "Serial Port 未跟随面板"
    assert w._sc_baud_combo.currentText() == "57600", "Baudrate 未跟随面板"
    assert w._sc_databit_combo.currentText() == "7", "Data bits 未跟随面板"
    assert w._sc_stopbit_combo.currentText() == "2", "Stop bits 未跟随面板"
    assert w._sc_parity_combo.currentText() == "Even", "Parity 未跟随面板"
    assert w._sc_flow_combo.currentText() == "RTS/CTS", "Flow 未跟随面板"
    assert w._sc_rx_toggle.value() == "HEX", "RX Format 未跟随面板"
    assert not w._sc_rx_show_time_cb.isChecked(), "Show Time 未跟随面板"
    assert w._sc_tx_toggle.value() == "HEX", "TX Format 未跟随面板"
    assert not w._sc_show_send_cb.isChecked(), "Show Sent 未跟随面板"
    ending_val = w._sc_ending_combo.itemData(w._sc_ending_combo.currentIndex()) or ""
    assert ending_val == "\n", "Line Ending 未跟随面板"
    assert panel["frame"].show_timestamp is False, "面板 show_timestamp 未应用到组件"
    assert not w._sc_auto_detect_cb.isEnabled(), "聚焦额外面板时 Auto-Detect 应禁用"
    assert not w._sc_rx_auto_flush_cb.isEnabled(), "聚焦额外面板时 Auto Flush 应禁用"
    assert not w._sc_show_system_cb.isEnabled(), "聚焦额外面板时 System Log 应禁用"

    # --- 主面板真值不被聚焦动作污染 ---
    primary_port_before = w._sc_primary_serial_cfg.get("port")
    assert primary_port_before != "COM5", "主面板真值被面板值污染"

    # --- 侧栏修改即时写回面板 config ---
    w._sc_on_rx_format_toggled("ASCII")
    assert panel["config"]["rx_hex"] is False, "RX Format 修改未写回面板 config"
    assert w._sc_rx_display_hex is False, "主面板 RX Format 被误写"
    w._sc_on_show_time_toggled(True)
    assert panel["config"]["show_timestamp"] is True, "Show Time 修改未写回面板 config"
    assert panel["frame"].show_timestamp is True, "Show Time 修改未同步组件"
    w._sc_on_line_ending_changed(0)  # index 0 = \r\n
    assert panel["config"]["line_ending"] == "\r\n", "Line Ending 修改未写回面板 config"
    w._sc_on_show_send_toggled(True)
    assert panel["config"]["show_send"] is True, "Show Sent 修改未写回面板 config"
    w._sc_databit_combo.setCurrentText("8")
    w._sc_sidebar_store_serial()
    assert panel["config"]["databit"] == "8", "Data bits 修改未写回面板 config"

    # --- rx_hex 数据路径生效 ---
    panel["config"]["rx_hex"] = True
    panel["frame"].flush_pending()
    logs_before = len(panel["frame"].all_logs)
    w._sc_extra_panel_on_data(panel, b"\x01\x02\xab")
    hex_lines = [raw for raw, _h, _n in panel["frame"].all_logs[logs_before:] if "01 02 ab" in raw]
    assert hex_lines, "rx_hex 数据路径未产生 hex 行"

    # --- show_send=False 不回显 ---
    panel["config"]["show_send"] = False
    w._sc_on_connect_toggle()  # Mock 连接面板
    app.processEvents()
    panel["frame"].flush_pending()
    logs_before = len(panel["frame"].all_logs)
    w._sc_send_to_focused_panel(b"hi\r\n", show_send=False, tx_hex=False)
    tx_lines = [raw for raw, _h, _n in panel["frame"].all_logs[logs_before:] if raw.startswith("[TX]") or "[TX]" in raw]
    assert not tx_lines, "show_send=False 仍回显 TX"

    # --- 切回主面板：侧栏恢复主面板真值 ---
    w._sc_on_primary_panel_clicked()
    app.processEvents()
    assert w._sc_sidebar_bound_index == 0, "切回主面板后侧栏绑定未恢复"
    assert w._sc_port_combo.currentText() == primary_port_before, "主面板 Port 未恢复"
    assert w._sc_auto_detect_cb.isEnabled(), "切回主面板后 Auto-Detect 应恢复可用"
    assert w._sc_rx_auto_flush_cb.isEnabled(), "切回主面板后 Auto Flush 应恢复可用"

    # --- 聚焦额外面板时采集持久化：主面板 serial 段不串值 ---
    w._sc_on_log_panel_clicked(panel, None)
    app.processEvents()
    persisted = w._sc_collect_persisted_state()
    assert persisted["serial"]["port"] == primary_port_before, "持久化主面板 port 被面板值串改"
    assert str(persisted["serial"]["baudrate"]) == str(w._sc_primary_serial_cfg.get("baudrate")), "持久化主面板 baudrate 串改"
    ep = persisted.get("extra_panels", [])
    assert ep and ep[0].get("port") == "COM5" and ep[0].get("rx_hex") is True, "面板 config 未随持久化携带"

    w.close()
    w.deleteLater()
    app.processEvents()


def test_sidebar_settings_dialog_forces_primary_view():
    """设置对话框路径：force_primary load/store 不串目标。"""
    app, w = _make_widget()

    panel = w._build_extra_log_panel({"title": "P3", "port": "COM7", "baudrate": 9600})
    w._sc_extra_log_panels.append(panel)
    w._sc_relayout_log_panels()
    w._sc_on_log_panel_clicked(panel, None)
    app.processEvents()
    assert w._sc_sidebar_bound_index == 1

    # 强制主面板视图（模拟打开设置对话框）
    w._sc_sidebar_load_focus(force_primary=True)
    assert w._sc_sidebar_bound_index == 0, "force_primary 未切回主面板绑定"
    assert w._sc_port_combo.currentText() != "COM7", "force_primary 后控件仍显示面板值"
    # 主面板视图下 store 不写面板 config
    w._sc_sidebar_store_serial()
    assert panel["config"]["port"] == "COM7", "force_primary 视图下 store 串到面板 config"

    # 恢复聚焦视图
    w._sc_sync_sidebar_to_focus()
    assert w._sc_sidebar_bound_index == 1, "恢复聚焦视图失败"
    assert w._sc_port_combo.currentText() == "COM7", "恢复后控件未回到面板值"

    w.close()
    w.deleteLater()
    app.processEvents()


if __name__ == "__main__":
    tests = [
        test_sidebar_follows_focus,
        test_sidebar_settings_dialog_forces_primary_view,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  [PASS] {fn.__name__}")
        except Exception:
            failed += 1
            print(f"  [FAIL] {fn.__name__}")
            traceback.print_exc()
    sys.exit(1 if failed else 0)
