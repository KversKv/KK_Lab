# 临时验证：Settings 全量持久化（字体/字号/换行/缓冲行数/默认自动滚动）+ 覆盖审计
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget, QTextEdit
from PySide6.QtCore import Signal

app = QApplication(sys.argv)

import ui.modules.serialCom_module.independent_window as isw
import ui.modules.serialCom_module.dialogs.panel_dialogs as panel_dlg
import ui.modules.serialCom_module.mixins.log_panel_mixin as lpm
import ui.modules.serialCom_module.mixins.connection_mixin as cm

isw.DEBUG_MOCK = True
panel_dlg.DEBUG_MOCK = True
lpm.DEBUG_MOCK = True
cm.DEBUG_MOCK = True

from ui.modules.serialCom_module.serialCom_module_frame import MODE_FULL, SerialComMixin


class _W(SerialComMixin, QWidget):
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    def append_log(self, msg):
        self._sc_append_system(msg, force_primary=True)


_tmpdir = tempfile.mkdtemp(prefix="sc_persist_")
_cfg_path = os.path.join(_tmpdir, "cfg.json")


def make_widget():
    w = _W()
    w._sc_persisted_path = lambda: _cfg_path
    w._sc_fallback_path = lambda: os.path.join(_tmpdir, "no_fallback.json")
    w._sc_migrate_legacy_config = lambda: None
    w.init_serial_connection(mode=MODE_FULL, prefix="Persist")
    root = QVBoxLayout(w)
    w.complete_serialComWidget(root)
    return w


def check_save():
    w = make_widget()
    w._sc_display_font = "Courier New"
    w._sc_display_font_size = 16
    w._sc_word_wrap = False
    w._sc_apply_max_log_lines(2000)
    w._sc_auto_scroll_default = False
    w._sc_save_persisted_state()
    with open(_cfg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    ui = data["ui"]
    assert ui["display_font"] == "Courier New"
    assert ui["display_font_size"] == 16
    assert ui["word_wrap"] is False
    assert ui["max_log_lines"] == 2000
    assert ui["auto_scroll_default"] is False
    w.close()
    w.deleteLater()


def check_restore():
    w = make_widget()
    assert w._sc_display_font == "Courier New"
    assert w._sc_display_font_size == 16
    assert w._sc_word_wrap is False
    assert w._sc_max_log_lines == 2000
    assert w._sc_auto_scroll_default is False
    p = w._sc_log_panel
    qss = p.log_edit.styleSheet()
    assert "Courier New" in qss, "font family not replayed to log edit"
    assert "16px" in qss, "font size not replayed to log edit"
    assert p.log_edit.lineWrapMode() == QTextEdit.NoWrap
    assert p.max_lines == 2000
    assert p.auto_scroll is False and not p.scroll_lock_btn.isChecked()
    w.close()
    w.deleteLater()
    app.processEvents()


def check_reset_replay():
    w = make_widget()
    w._sc_apply_persisted_state(w._sc_default_persisted_state())
    assert w._sc_display_font == "Consolas"
    assert w._sc_display_font_size == 11
    p = w._sc_log_panel
    qss = p.log_edit.styleSheet()
    assert "Consolas" in qss and "11px" in qss, "reset must restore default font QSS"
    assert p.log_edit.lineWrapMode() == QTextEdit.WidgetWidth
    assert p.max_lines == w._SC_MAX_LOG_LINES_DEFAULT
    assert p.auto_scroll is True and p.scroll_lock_btn.isChecked()
    w.close()
    w.deleteLater()
    app.processEvents()


def check_settings_coverage():
    w = make_widget()
    state = w._sc_collect_persisted_state()
    ui_keys = {
        "rx_display_hex", "tx_display_hex", "show_timestamp", "use_ntp",
        "line_ending", "show_send", "line_by_line", "show_line_num",
        "display_font", "display_font_size", "word_wrap", "max_log_lines",
        "auto_scroll_default", "log_auto_save", "log_save_path",
        "sidebar_visible", "footer_visible",
    }
    missing_ui = ui_keys - set(state["ui"].keys())
    assert not missing_ui, f"ui keys missing: {missing_ui}"
    serial_keys = {
        "port", "baudrate", "auto_detect", "databits", "stopbits",
        "parity", "flow_control", "auto_detect_config",
    }
    missing_serial = serial_keys - set(state["serial"].keys())
    assert not missing_serial, f"serial keys missing: {missing_serial}"
    ad = state["serial"]["auto_detect_config"]
    ad_keys = {
        "runtime_redetect_enabled", "candidate_baudrates", "lock_threshold",
        "bad_threshold", "bad_windows_to_suspect", "suspect_windows_to_scan",
        "monitor_window_max_time_ms", "switch_cooldown_ms",
        "switch_score_margin", "confirm_scan_rounds",
    }
    missing_ad = ad_keys - set(ad.keys())
    assert not missing_ad, f"auto-detect keys missing: {missing_ad}"
    w.close()
    w.deleteLater()
    app.processEvents()


check_save()
check_restore()
check_reset_replay()
check_settings_coverage()
print("ALL PASS")
