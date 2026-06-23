#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 4 回归：SerialComMixin 多 Mixin 装配体实例化与构建冒烟。

验证 7 个 Mixin（Connection/Toolbar/LogPanel/FilterSave/Send/Chart/Script）
装配后 complete_serialComWidget 能正常构建全部子区，关键子控件存在，
且日志追加 / 持久化保存 / 关闭清理不抛异常。

可独立运行：
    python tests/test_serialcom_mixin_assembly.py
也可被 pytest 收集：
    pytest tests/test_serialcom_mixin_assembly.py
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

from ui.modules.serialCom_module.serialCom_module_frame import (
    MODE_FULL,
    MODE_INLINE,
    SerialComMixin,
)


class _SmokeWidget(SerialComMixin, QWidget):
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    def append_log(self, msg):
        self._sc_append_system(msg, force_primary=True)


def _ensure_app():
    return QApplication.instance() or QApplication([])


def test_compile_mixin_files():
    import py_compile

    base = os.path.join(_ROOT, "ui", "modules", "serialCom_module")
    targets = [
        os.path.join(base, "serialCom_module_frame.py"),
        os.path.join(base, "widgets.py"),
        os.path.join(base, "mixins", "connection_mixin.py"),
        os.path.join(base, "mixins", "toolbar_mixin.py"),
        os.path.join(base, "mixins", "log_panel_mixin.py"),
        os.path.join(base, "mixins", "filter_save_mixin.py"),
        os.path.join(base, "mixins", "send_mixin.py"),
        os.path.join(base, "mixins", "chart_mixin.py"),
        os.path.join(base, "mixins", "script_mixin.py"),
    ]
    for t in targets:
        py_compile.compile(t, doraise=True)


def test_assembly_builds_all_sections():
    app = _ensure_app()
    w = _SmokeWidget()
    w.init_serial_connection(mode=MODE_FULL, prefix="Smoke")
    root = QVBoxLayout(w)
    w.complete_serialComWidget(root)

    assert w._sc_toolbar is not None, "_build_sc_toolbar 未构建 (ToolbarMixin)"
    assert w._sc_sidebar_widget is not None, "_build_sc_sidebar 未构建 (ToolbarMixin)"
    assert w._sc_log_area is not None, "_build_sc_log_area 未构建 (LogPanelMixin)"
    assert w._sc_send_area is not None, "_build_sc_send_area 未构建 (SendMixin)"
    assert w._sc_quick_area is not None, "_build_sc_quick_commands 未构建 (SendMixin)"
    assert isinstance(w._sc_qc_data, dict), "_sc_qc_default_data 未生效 (SendMixin)"
    assert isinstance(w._sc_script_data, dict), "_sc_script_default_data 未生效 (ScriptMixin)"
    assert w._sc_script_timer is not None, "脚本定时器未创建 (ScriptMixin)"
    assert w._sc_auto_baud_monitor is not None, "AutoBaudMonitor 未创建 (ConnectionMixin)"

    w._sc_append_system("[INFO] assembly smoke ok", force_primary=True)

    w._sc_save_persisted_state()
    w.close_serial()
    w.deleteLater()
    app.processEvents()


def test_inline_mode_builds_connection_widgets():
    app = _ensure_app()
    w = _SmokeWidget()
    w.init_serial_connection(mode=MODE_INLINE, prefix="Inline")
    root = QVBoxLayout(w)
    w.build_serial_connection_widgets(root)
    assert w.serial_combo is not None, "inline serial_combo 未构建 (ConnectionMixin)"
    assert w.serial_search_btn is not None, "inline serial_search_btn 未构建 (ConnectionMixin)"
    w.deleteLater()
    app.processEvents()


def _run_standalone():
    failed = False
    for name, fn in [
        ("test_compile_mixin_files", test_compile_mixin_files),
        ("test_assembly_builds_all_sections", test_assembly_builds_all_sections),
        ("test_inline_mode_builds_connection_widgets", test_inline_mode_builds_connection_widgets),
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
    print("=== SerialComMixin Assembly Smoke (standalone) ===")
    sys.exit(1 if _run_standalone() else 0)
