# -*- coding: utf-8 -*-
"""临时调试：SerialCom 发送框 ↑/↓ 历史导航验证（QTest 真实按键路径）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget


def _ensure_app():
    return QApplication.instance() or QApplication([])


def main():
    import ui.modules.serialCom_module.serialCom_module_frame as frame
    import ui.modules.serialCom_module.mixins.log_panel_mixin as lpm
    import ui.modules.serialCom_module.mixins.connection_mixin as cm

    frame.DEBUG_MOCK = True
    lpm.DEBUG_MOCK = True
    cm.DEBUG_MOCK = True

    from ui.modules.serialCom_module.serialCom_module_frame import MODE_FULL, SerialComMixin

    class _W(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def append_log(self, msg):
            self._sc_append_system(msg, force_primary=True)

    app = _ensure_app()
    w = _W()
    w.init_serial_connection(mode=MODE_FULL, prefix="HistNav")
    root = QVBoxLayout(w)
    w.complete_serialComWidget(root)
    w.show()
    app.processEvents()

    # 插桩：记录 eventFilter 是否收到发送框的按键
    hits = []
    orig_ef = w.eventFilter

    def _spy(obj, event):
        if obj is w._sc_send_input and event.type() == QEvent.KeyPress:
            hits.append(event.key())
        return orig_ef(obj, event)

    w.eventFilter = _spy

    # 模拟历史：最新在 index 0
    w._sc_send_history = ["Test2", "IBRT_UI:pairing_mode_test", "test2", "test1"]
    w._sc_history_combo.blockSignals(True)
    w._sc_history_combo.clear()
    w._sc_history_combo.addItems(w._sc_send_history)
    w._sc_history_combo.setCurrentIndex(-1)
    w._sc_history_combo.blockSignals(False)
    w._sc_send_input.clear()

    le = w._sc_send_input
    le.setFocus(Qt.OtherFocusReason)
    app.processEvents()
    print("focusWidget:", app.focusWidget().__class__.__name__,
          "is lineEdit:", app.focusWidget() is le)

    def _press(key, target=None):
        QTest.keyClick(target or le, key)
        app.processEvents()
        return le.text()

    # 路径 A：按键投递到 lineEdit —— ↑ 应从最新一条开始逐条向更早浏览
    assert _press(Qt.Key_Up) == "Test2", f"Up #1 应显示最新历史, 实际={le.text()!r}"
    assert _press(Qt.Key_Up) == "IBRT_UI:pairing_mode_test", "Up #2 应显示次新历史"
    assert _press(Qt.Key_Up) == "test2", "Up #3 应继续向更早"
    # ↓ 应反向回到更新，越过最新后恢复浏览前输入（空）
    assert _press(Qt.Key_Down) == "IBRT_UI:pairing_mode_test", "Down #1 应回退一条"
    assert _press(Qt.Key_Down) == "Test2", "Down #2 应回退到最新"
    assert _press(Qt.Key_Down) == "", "Down #3 应恢复浏览前输入"

    # 路径 B：按键投递到 combo 本体（真机 focusWidget 常为 combo）
    combo = w._sc_history_combo
    assert _press(Qt.Key_Up, combo) == "Test2", f"combo Up #1 应显示最新历史, 实际={le.text()!r}"
    assert _press(Qt.Key_Up, combo) == "IBRT_UI:pairing_mode_test", "combo Up #2 应显示次新历史"
    assert _press(Qt.Key_Down, combo) == "Test2", "combo Down #1 应回退一条"
    assert _press(Qt.Key_Down, combo) == "", "combo Down #2 应恢复浏览前输入"

    print("eventFilter KeyPress hits:", hits)
    print("  [PASS] test_history_up_down_nav")
    w.close()


if __name__ == "__main__":
    main()
