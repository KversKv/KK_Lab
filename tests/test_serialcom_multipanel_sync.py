#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多串口同步回归：独立浮窗按钮/行为 与 主窗口顶部控制跟随聚焦。

覆盖：
1. _IndependentSerialWindow 补齐 Filter/Copy/Export/Clear/Auto-scroll 按钮，
   auto-scroll 支持按钮开关 + 用户滚动检测（离底暂停 / 回底恢复），
   Clear 重置滚动锁，Filter 过滤/还原。
2. 主窗口顶部 Connect/Pause/Stop 跟随 _sc_active_log_panel_index：
   聚焦额外面板时控制面板连接与暂停，焦点切换时按钮文本/勾选同步。

可独立运行：
    python tests/test_serialcom_multipanel_sync.py
也可被 pytest 收集：
    pytest tests/test_serialcom_multipanel_sync.py
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


def test_independent_window_buttons_and_autoscroll():
    from ui.modules.serialCom_module.serialCom_module_frame import _IndependentSerialWindow

    app = _ensure_app()
    win = _IndependentSerialWindow({"title": "T", "port": "COM1", "baudrate": 115200})
    win.resize(500, 240)
    win.show()
    app.processEvents()

    assert win._filter_btn.isCheckable(), "Filter 按钮缺失/不可勾选"
    assert win._scroll_btn.isCheckable() and win._scroll_btn.isChecked(), "Auto-scroll 按钮初始态错误"

    for i in range(80):
        win._append(f"[RX] line {i}")
    app.processEvents()
    assert len(win._all_logs) == 80, "_all_logs 未记录"

    sb = win._log_edit.verticalScrollBar()
    assert sb is not None and sb.maximum() > 0, "滚动条无有效范围"

    # 用户上滚 -> 暂停自动滚动
    win._on_user_scroll(0)
    assert win._auto_scroll is False and not win._scroll_btn.isChecked(), "上滚未暂停 auto-scroll"
    # 回到底部 -> 恢复
    win._on_user_scroll(sb.maximum())
    assert win._auto_scroll is True and win._scroll_btn.isChecked(), "回底未恢复 auto-scroll"
    # 按钮关闭 -> 停止跟随
    win._scroll_btn.click()
    app.processEvents()
    assert win._auto_scroll is False, "按钮关闭未生效"
    # 贴底关闭后来数据 -> 不得复活且画面冻结（Qt 钉底对抗）
    frozen_value = sb.value()
    win._append("[RX] while off")
    app.processEvents()
    assert win._auto_scroll is False and not win._scroll_btn.isChecked(), "关闭后被新数据复活"
    assert sb.value() == frozen_value, "关闭后画面未冻结"
    # 用户真实回底 -> 恢复
    sb.setValue(sb.maximum())
    app.processEvents()
    assert win._auto_scroll is True and win._scroll_btn.isChecked(), "真实回底未恢复"
    win._on_scroll_btn_toggled(True)
    assert win._auto_scroll is True, "按钮开启未生效"

    # 过滤：'line 1' 命中 line 1 + line 10..19 共 11 行
    win._filter_input.setText("line 1")
    win._apply_filter()
    assert win._filter_match_label.text() == "11 matches", f"过滤计数错误: {win._filter_match_label.text()}"
    win._toggle_filter(False)
    assert win._filter_match_label.text() == "", "关闭过滤未清空计数"

    # Clear 重置滚动锁与缓存
    win._clear_log()
    assert win._auto_scroll is True and win._scroll_btn.isChecked(), "Clear 未重置 auto-scroll"
    assert not win._all_logs, "Clear 未清空 _all_logs"

    win.close()
    win.deleteLater()
    app.processEvents()


def test_top_controls_follow_focus():
    import ui.modules.serialCom_module.serialCom_module_frame as frame
    import ui.modules.serialCom_module.mixins.log_panel_mixin as lpm
    import ui.modules.serialCom_module.mixins.connection_mixin as cm

    frame.DEBUG_MOCK = True
    lpm.DEBUG_MOCK = True
    cm.DEBUG_MOCK = True

    from ui.modules.serialCom_module.serialCom_module_frame import MODE_FULL, SerialComMixin

    class _SmokeWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def append_log(self, msg):
            self._sc_append_system(msg, force_primary=True)

    app = _ensure_app()
    w = _SmokeWidget()
    w.init_serial_connection(mode=MODE_FULL, prefix="Smoke")
    root = QVBoxLayout(w)
    w.complete_serialComWidget(root)
    w.resize(900, 500)
    w.show()
    app.processEvents()

    config = {
        "title": "P2", "port": "COM5", "baudrate": 115200,
        "databit": 8, "stopbit": "1", "parity": "None", "flow": "None",
    }
    panel = w._build_extra_log_panel(config)
    w._sc_extra_log_panels.append(panel)
    w._sc_relayout_log_panels()

    # 聚焦额外面板 -> 顶部按钮反映面板状态（未连接）
    w._sc_on_log_panel_clicked(panel, None)
    assert w._sc_active_extra_panel() is panel, "聚焦面板解析失败"
    assert w._sc_connect_btn.text() == "Connect", "聚焦未连接面板时按钮应为 Connect"

    # 顶部 Connect -> 连接聚焦面板（Mock）
    w._sc_on_connect_toggle()
    assert panel.get("session_id") is not None, "面板 Mock 连接未建立会话"
    assert w._sc_connect_btn.text() == "Disconnect", "面板连接后按钮未变 Disconnect"

    # Pause 分发到面板且不影响主串口
    w._sc_on_pause(True)
    assert panel["paused"] is True and w._sc_paused is False, "Pause 未分发到聚焦面板"
    rx_before = panel["rx_bytes"]
    w._sc_extra_panel_on_data(panel, b"hello\n")
    assert panel["rx_bytes"] == rx_before, "面板暂停时仍接收数据"

    # 切回主面板 -> 按钮恢复主串口状态
    w._sc_on_primary_panel_clicked(None)
    assert w._sc_active_extra_panel() is None, "主面板聚焦解析失败"
    assert w._sc_connect_btn.text() == "Connect", "切回主面板后按钮未恢复"
    assert not w._sc_pause_btn.isChecked(), "切回主面板后 Pause 勾选未恢复"

    # 再次聚焦面板 -> Pause 状态同步回按钮
    w._sc_on_log_panel_clicked(panel, None)
    assert w._sc_pause_btn.isChecked() and w._sc_pause_btn.text() == "Resume", "面板 Pause 状态未同步到按钮"

    # Stop 断开聚焦面板
    w._sc_on_stop()
    assert w._sc_connect_btn.text() == "Connect", "Stop 后按钮未恢复 Connect"
    assert panel.get("session_id") is None, "Stop 后面板会话未移除"

    # 面板 auto-scroll：贴底关闭后来数据不得复活且画面冻结
    w._sc_on_primary_panel_clicked(None)
    for i in range(100):
        w._sc_extra_panel_append_log(panel, f"[RX] line {i}")
    w._sc_flush_extra_panels()
    app.processEvents()
    psb = panel["log_edit"].verticalScrollBar()
    assert psb.value() == psb.maximum() > 0, "面板初始未跟随到底"
    panel["scroll_btn"].click()
    app.processEvents()
    assert panel["auto_scroll"] is False, "面板按钮关闭未生效"
    frozen = psb.value()
    w._sc_extra_panel_append_log(panel, "[RX] while off")
    w._sc_flush_extra_panels()
    app.processEvents()
    assert panel["auto_scroll"] is False and not panel["scroll_btn"].isChecked(), "面板关闭后被新数据复活"
    assert psb.value() == frozen, "面板关闭后画面未冻结"
    psb.setValue(psb.maximum())
    app.processEvents()
    assert panel["auto_scroll"] is True and panel["scroll_btn"].isChecked(), "面板真实回底未恢复"

    w._sc_save_persisted_state()
    w.close_serial()
    w.deleteLater()
    app.processEvents()


def _run_standalone():
    failed = False
    for name, fn in [
        ("test_independent_window_buttons_and_autoscroll", test_independent_window_buttons_and_autoscroll),
        ("test_top_controls_follow_focus", test_top_controls_follow_focus),
    ]:
        try:
            fn()
            print(f"  [PASS] {name}")
        except Exception:
            print(f"  [FAIL] {name}")
            print(traceback.format_exc()[:3000])
            failed = True
    return failed


if __name__ == "__main__":
    print("=== SerialCom Multi-Panel Sync Smoke (standalone) ===")
    sys.exit(1 if _run_standalone() else 0)
