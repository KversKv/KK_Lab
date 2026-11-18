# 临时验证：Clear 后已应用的 Filter 仍生效（offscreen）
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from ui.modules.serialCom_module.serial_log_panel import SerialLogPanel


def check_filter_kept():
    p = SerialLogPanel()
    p.show()
    p.set_filter_visible(True)
    p.filter_input.setText("KEEP")
    p.apply_filter()
    p.append_log("[RX] KEEP one")
    p.append_log("[RX] drop two")
    p.flush_pending()
    assert "KEEP one" in p.log_edit.toPlainText()
    assert "drop two" not in p.log_edit.toPlainText()

    p.clear_logs()
    assert p.filter_applied_pattern == "KEEP", "applied filter wiped by clear"
    assert p.filter_match_label.text() == "Matched: 0 lines"
    assert p.is_filter_active()

    p.append_log("[RX] drop three")
    p.append_log("[RX] KEEP four")
    p.flush_pending()
    text = p.log_edit.toPlainText()
    assert "KEEP four" in text, f"filter not applied after clear: {text!r}"
    assert "drop three" not in text, f"non-matching line leaked: {text!r}"
    assert p.filter_match_label.text() == "Matched: 1 lines"
    p.deleteLater()


def check_highlight_only_kept():
    p = SerialLogPanel()
    p.show()
    p.set_filter_visible(True)
    p.filter_input.setText("MARK")
    p.filter_highlight_only_cb.setChecked(True)
    p.apply_filter()
    p.clear_logs()
    assert p.is_highlight_only_active(), "highlight-only mode wiped by clear"
    p.append_log("[RX] MARK five")
    p.append_log("[RX] plain six")
    p.flush_pending()
    text = p.log_edit.toPlainText()
    assert "MARK five" in text and "plain six" in text
    p.deleteLater()


def check_context_filter_kept():
    p = SerialLogPanel()
    p.show()
    p.set_filter_visible(True)
    p.filter_input.setText("KEEP")
    p.filter_before_spin.setValue(1)
    p.apply_filter()
    p.clear_logs()
    assert p.filter_applied_before == 1
    p.append_log("[RX] ctx before")
    p.append_log("[RX] KEEP hit")
    p.append_log("[RX] unrelated")
    p.flush_pending()
    text = p.log_edit.toPlainText()
    assert "ctx before" in text and "KEEP hit" in text
    assert "unrelated" not in text
    p.deleteLater()


def check_hide_filter_still_resets():
    p = SerialLogPanel()
    p.show()
    p.set_filter_visible(True)
    p.filter_input.setText("KEEP")
    p.apply_filter()
    p.set_filter_visible(False)
    assert p.filter_applied_pattern == "", "hide filter should still reset"
    p.clear_logs()
    assert p.filter_match_label.text() == ""
    p.deleteLater()


check_filter_kept()
check_highlight_only_kept()
check_context_filter_kept()
check_hide_filter_still_resets()
print("ALL PASS")
