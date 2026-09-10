#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多串口同步回归：独立浮窗按钮/行为 与 主窗口顶部控制跟随聚焦。

覆盖：
1. _IndependentSerialWindow 补齐 Filter/Copy/Export/Clear/Auto-scroll 按钮，
   auto-scroll 支持按钮开关 + 用户滚动检测（离底暂停 / 回底恢复），
   Clear 重置滚动锁，Filter 过滤/还原。
2. 主窗口顶部 Connect/Pause/Stop 跟随 _sc_active_log_panel_index：
   聚焦额外面板时控制面板连接/显示暂停/丢弃接收，焦点切换时按钮文本/勾选同步。
   Pause=冻结显示但保留数据；Stop=保持连接丢弃 RX 且可恢复；Disconnect=断连串口。

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

    panel = win._panel
    assert panel.filter_btn.isCheckable(), "Filter 按钮缺失/不可勾选"
    assert panel.scroll_lock_btn.isCheckable() and panel.scroll_lock_btn.isChecked(), "Auto-scroll 按钮初始态错误"

    for i in range(80):
        panel.append_log(f"[RX] line {i}")
    panel.flush_pending()
    app.processEvents()
    assert len(panel.all_logs) == 80, "all_logs 未记录"

    sb = panel.log_edit.verticalScrollBar()
    assert sb is not None and sb.maximum() > 0, "滚动条无有效范围"

    # 用户上滚 -> 暂停自动滚动
    panel._on_user_scroll(0)
    assert panel.auto_scroll is False and not panel.scroll_lock_btn.isChecked(), "上滚未暂停 auto-scroll"
    # 回到底部 -> 恢复
    panel._on_user_scroll(sb.maximum())
    assert panel.auto_scroll is True and panel.scroll_lock_btn.isChecked(), "回底未恢复 auto-scroll"
    # 按钮关闭 -> 停止跟随
    panel.scroll_lock_btn.click()
    app.processEvents()
    assert panel.auto_scroll is False, "按钮关闭未生效"
    # 贴底关闭后来数据 -> 不得复活且画面冻结（Qt 钉底对抗）
    frozen_value = sb.value()
    panel.append_log("[RX] while off")
    panel.flush_pending()
    app.processEvents()
    assert panel.auto_scroll is False and not panel.scroll_lock_btn.isChecked(), "关闭后被新数据复活"
    assert sb.value() == frozen_value, "关闭后画面未冻结"
    # 用户真实回底 -> 恢复
    sb.setValue(sb.maximum())
    app.processEvents()
    assert panel.auto_scroll is True and panel.scroll_lock_btn.isChecked(), "真实回底未恢复"
    panel._on_scroll_btn_clicked(True)
    assert panel.auto_scroll is True, "按钮开启未生效"

    # 过滤：'line 1' 命中 line 1 + line 10..19 共 11 行
    panel.filter_input.setText("line 1")
    panel.apply_filter()
    assert panel.filter_match_label.text() == "Matched: 11 lines", f"过滤计数错误: {panel.filter_match_label.text()}"
    panel.set_filter_visible(False)
    assert panel.filter_match_label.text() == "", "关闭过滤未清空计数"

    # Clear 重置滚动锁与缓存
    panel.clear_logs()
    assert panel.auto_scroll is True and panel.scroll_lock_btn.isChecked(), "Clear 未重置 auto-scroll"
    assert not panel.all_logs, "Clear 未清空 all_logs"

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

    # Pause 分发到面板且不影响主串口；新语义：冻结显示但保留数据
    w._sc_on_pause(True)
    assert panel["paused"] is True and w._sc_paused is False, "Pause 未分发到聚焦面板"
    assert panel["frame"].display_paused is True, "Pause 未同步到组件 display_paused"
    panel["frame"].flush_pending()  # 先冲掉 connect 期间残留的 [INFO]，建立空基线
    app.processEvents()
    rx_before = panel["frame"].rx_bytes
    logs_before = len(panel["frame"].all_logs)
    w._sc_extra_panel_on_data(panel, b"hello\n")
    assert panel["frame"].rx_bytes > rx_before, "Pause 应保留 RX 字节计数"
    assert len(panel["frame"].all_logs) > logs_before, "Pause 应保留 RX 数据到 all_logs"
    assert not panel["frame"].pending_html, "Pause 期间不应渲染到视图"

    # 切回主面板 -> 按钮恢复主串口状态
    w._sc_on_primary_panel_clicked()
    assert w._sc_active_extra_panel() is None, "主面板聚焦解析失败"
    assert w._sc_connect_btn.text() == "Connect", "切回主面板后按钮未恢复"
    assert not w._sc_pause_btn.isChecked(), "切回主面板后 Pause 勾选未恢复"

    # 再次聚焦面板 -> Pause 状态同步回按钮
    w._sc_on_log_panel_clicked(panel, None)
    assert w._sc_pause_btn.isChecked() and w._sc_pause_btn.text() == "Resume", "面板 Pause 状态未同步到按钮"

    # 恢复 Pause -> 全量重建，日志不丢失
    w._sc_on_pause(False)
    assert panel["frame"].display_paused is False, "Pause 恢复失败"
    assert not w._sc_pause_btn.isChecked() and w._sc_pause_btn.text() == "Pause", "Pause 恢复后按钮未同步"

    # Stop 新语义：保持连接但丢弃 RX；再次点击恢复接收
    w._sc_on_stop(True)
    assert panel["stopped"] is True, "Stop 未分发到聚焦面板"
    assert panel.get("session_id") is not None, "Stop 不应断开连接"
    assert w._sc_stop_btn.isChecked() and w._sc_stop_btn.text() == "Resume", "Stop 按钮状态未同步"
    rx_before = panel["frame"].rx_bytes
    w._sc_extra_panel_on_data(panel, b"dropped\n")
    assert panel["frame"].rx_bytes == rx_before, "Stop 期间应丢弃 RX 数据"
    w._sc_on_stop(False)
    assert panel["stopped"] is False and not w._sc_stop_btn.isChecked(), "Stop 恢复失败"
    w._sc_extra_panel_on_data(panel, b"resumed\n")
    assert panel["frame"].rx_bytes > rx_before, "Stop 恢复后应继续接收"

    # Disconnect 断开聚焦面板
    w._sc_on_connect_toggle()
    assert w._sc_connect_btn.text() == "Connect", "Disconnect 后按钮未恢复 Connect"
    assert panel.get("session_id") is None, "Disconnect 后面板会话未移除"

    # 面板 auto-scroll：贴底关闭后来数据不得复活且画面冻结
    w._sc_on_primary_panel_clicked()
    for i in range(100):
        w._sc_extra_panel_append_log(panel, f"[RX] line {i}")
    panel["frame"].flush_pending()
    app.processEvents()
    psb = panel["log_edit"].verticalScrollBar()
    assert psb.value() == psb.maximum() > 0, "面板初始未跟随到底"
    panel["scroll_btn"].click()
    app.processEvents()
    assert panel["frame"].auto_scroll is False, "面板按钮关闭未生效"
    frozen = psb.value()
    w._sc_extra_panel_append_log(panel, "[RX] while off")
    panel["frame"].flush_pending()
    app.processEvents()
    assert panel["frame"].auto_scroll is False and not panel["scroll_btn"].isChecked(), "面板关闭后被新数据复活"
    assert psb.value() == frozen, "面板关闭后画面未冻结"
    psb.setValue(psb.maximum())
    app.processEvents()
    assert panel["frame"].auto_scroll is True and panel["scroll_btn"].isChecked(), "面板真实回底未恢复"

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
