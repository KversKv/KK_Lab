# -*- coding: utf-8 -*-
"""过滤快捷键/过滤匹配高亮/手动保存/清屏/滚动/复制/导出。"""

import json
import os
import re
import time
import uuid as _uuid
from datetime import datetime

import serial
import serial.tools.list_ports

from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDialog,
    QDialogButtonBox, QFileDialog, QFrame, QGridLayout, QGraphicsBlurEffect,
    QGraphicsDropShadowEffect, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QMessageBox, QPlainTextEdit,
    QPushButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter, QTabBar,
    QTabWidget, QTableWidget, QTableWidgetItem, QTextEdit, QToolButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)
from PySide6.QtCore import (
    Property, QEasingCurve, QMimeData, QObject, QPoint, QPropertyAnimation,
    QRect, QRectF, QSize, Qt, QThread, QTimer, Signal,
)
from PySide6.QtGui import (
    QAction, QColor, QCursor, QFont, QIcon, QKeySequence, QPainter, QPen,
    QPixmap, QShortcut,
)
from PySide6.QtSvg import QSvgRenderer

from debug_config import DEBUG_MOCK
from log_config import get_logger
from version import __version__ as _APP_VERSION
from ui.utils.icon_utils import (
    tinted_svg_icon as _tinted_svg_icon,
    tinted_svg_pixmap as _tinted_svg_pixmap,
)
from core.auto_baud_detector import (
    AUTO_BAUD_CONFIG, AutoBaudMonitor, AutoBaudScanWorker, AutoBaudState,
    score_rx_data,
)
from ui.modules.serialCom_module.widgets import (
    _FramelessChromeDialog,
    _MixinSerialSettingsDialog,
    _SERIAL_BTN_FIXED_WIDTH,
    _SearchSerialPortWorker,
    _SerialSearchButton,
    _update_serial_btn_state,
)
from ui.modules.serialCom_module.serialCom_module_frame import (
    MODE_FULL,
    MODE_INLINE,
    MODE_SEARCH_SELECT,
    _LINK_ICON_PATH,
    _SEARCH_ICON_PATH,
    _SERIAL_BTN_HEIGHT,
    _SERIAL_BTN_ICON_SIZE,
    _SERIAL_BTN_RADIUS,
    _SVG_COMMON_DIR,
    _SVG_LOGS_DIR,
    _SVG_SERIAL_DIR,
    _UNLINK_ICON_PATH,
    DARK_CARD_STYLE,
    _CLR_BG_CARD,
    _CLR_BG_LOG,
    _CLR_BG_MAIN,
    _CLR_BG_PANEL,
    _CLR_BLUE,
    _CLR_BORDER,
    _CLR_BORDER_HOVER,
    _CLR_BORDER_SOFT,
    _CLR_CONNECT_BG,
    _CLR_CONNECT_FG,
    _CLR_CONNECT_TEXT,
    _CLR_CURSOR,
    _CLR_DISCONNECT_TEXT,
    _CLR_ERROR,
    _CLR_FILTER_BG,
    _CLR_FILTER_BORDER,
    _CLR_FILTER_TEXT,
    _CLR_INPUT_BG,
    _CLR_INPUT_TEXT,
    _CLR_ROSE_ICON,
    _CLR_RX,
    _CLR_SCROLLBAR,
    _CLR_SCROLLBAR_HV,
    _CLR_SELECTION_BG,
    _CLR_SELECTION_TEXT,
    _CLR_SEND_BG,
    _CLR_SEND_HOVER,
    _CLR_SEND_PRESS,
    _CLR_TEXT_ACCENT,
    _CLR_TEXT_BODY,
    _CLR_TEXT_BTN,
    _CLR_TEXT_BTN_LOG,
    _CLR_TEXT_INFO,
    _CLR_TEXT_LABEL,
    _CLR_TEXT_LINENO,
    _CLR_TEXT_MUTED,
    _CLR_TEXT_SUBTITLE,
    _CLR_TEXT_TIME,
    _CLR_TEXT_TITLE,
    _CLR_TEXT_WHITE,
    _CLR_TOGGLE_ON,
    _CLR_TX,
    _CLR_WARN_ICON,
    _CLR_WARNING,
    _DLG_STYLE,
    _SERIAL_BTN_HEIGHT,
    _SERIAL_BTN_ICON_SIZE,
    _SERIAL_BTN_RADIUS,
    _TERM_FONT,
    _UI_FONT,
    _serial_connect_style,
    _serial_disconnect_style,
    _serial_search_style,
    body_splitter_style,
    center_vsplitter_style,
    center_widget_style,
    checkbox_style,
    compact_spinbox_style,
    dialog_backdrop_style,
    frameless_chrome_style,
    script_editor_dialog_style,
    dialog_cancel_button_style,
    dialog_line_edit_style,
    dialog_ok_button_style,
    extra_log_error_color,
    field_label_style,
    filter_input_style,
    filter_match_label_style,
    history_combo_style,
    inline_serial_label_style,
    inline_serial_search_button_extra_style,
    log_color_info_style,
    log_color_info_text,
    log_document_style,
    log_edit_style,
    log_frame_style,
    log_panel_button_style,
    log_title_style,
    log_title_icon_color,
    log_toolbar_button_style,
    log_icon_button_style,
    main_connect_button_style,
    project_tabs_style,
    quick_action_overlay_style,
    quick_action_overlay_container_style,
    quick_add_button_style,
    quick_group_button_style,
    quick_button_container_style,
    quick_button_scroll_style,
    quick_cmd_dialog_style,
    quick_command_button_style,
    quick_combo_style,
    quick_group_combo_bg_style,
    quick_commands_panel_style,
    quick_preview_popup_shadow,
    quick_preview_popup_style,
    quick_toolbar_button_style,
    bottom_tabs_style,
    section_card_style,
    section_card_shadow,
    section_header_divider_style,
    panel_divider_style,
    script_stop_button_style,
    script_add_step_button_style,
    section_title_style,
    send_button_style,
    separator_style,
    sidebar_toggle_button_style,
    auto_scroll_button_style,
    sidebar_toggle_icon_colors,
    auto_scroll_icon_colors,
    sidebar_wrapper_style,
    small_label_style,
    status_bar_style,
    status_label_style,
    thin_scrollbar_style,
    toolbar_connect_button_style,
    toolbar_style,
    toggle_colors,
    transparent_background_style,
    transparent_scroll_area_style,
    transparent_toolbar_button_style,
    unit_label_style,
    SERIAL_SCROLLBAR_STYLE,
    SerialDarkComboBox,
    SerialHistoryComboBox,
    _CLR_HISTORY_COMBO_BG
)

logger = get_logger(__name__)


class FilterSaveMixin:
    """过滤快捷键/过滤匹配高亮/手动保存/清屏/滚动/复制/导出。"""

    def _sc_install_filter_shortcut(self):
        host_widgets = []
        if getattr(self, "_sc_log_area", None) is not None:
            host_widgets.append(self._sc_log_area)
        if getattr(self, "_sc_send_input", None) is not None:
            host_widgets.append(self._sc_send_input)

        self._sc_filter_shortcuts = []
        for host in host_widgets:
            sc = QShortcut(QKeySequence("Ctrl+F"), host)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(self._sc_toggle_filter_shortcut)
            self._sc_filter_shortcuts.append(sc)

    def _sc_toggle_filter_shortcut(self):
        btn = getattr(self, "_sc_filter_btn", None)
        if btn is None:
            return
        btn.click()
        if btn.isChecked():
            input_widget = getattr(self, "_sc_filter_input", None)
            if input_widget is not None:
                input_widget.setFocus(Qt.ShortcutFocusReason)
                input_widget.selectAll()

    # --- action handlers ---


    def _sc_on_filter_toggle(self, checked):
        self._sc_filter_row.setVisible(checked)
        if not checked:
            self._sc_filter_input.clear()
            self._sc_filter_match_label.setText("")
            self._sc_filter_dirty = False
            self._sc_filter_last_count = len(self._sc_all_logs)
            self._sc_reset_applied_filter()
            self._sc_rebuild_log_view()

    def _sc_reset_applied_filter(self):
        self._sc_filter_applied_pattern = ""
        self._sc_filter_applied_use_regex = False
        self._sc_filter_applied_case = False
        self._sc_filter_applied_invert = False
        self._sc_filter_applied_before = 0
        self._sc_filter_applied_after = 0

    def _sc_filter_inputs_match_applied(self):
        return (
            self._sc_filter_input.text().strip() == self._sc_filter_applied_pattern
            and self._sc_filter_regex_cb.isChecked() == self._sc_filter_applied_use_regex
            and self._sc_filter_case_cb.isChecked() == self._sc_filter_applied_case
            and self._sc_filter_invert_cb.isChecked() == self._sc_filter_applied_invert
            and self._sc_filter_before_spin.value() == self._sc_filter_applied_before
            and self._sc_filter_after_spin.value() == self._sc_filter_applied_after
        )

    def _sc_update_pending_hint(self):
        if not self._sc_filter_row.isVisible():
            return
        if self._sc_filter_inputs_match_applied():
            return
        self._sc_filter_match_label.setText("Press Enter to apply")

    def _sc_on_filter_input_changed(self, _text=None):
        self._sc_update_pending_hint()

    def _sc_on_filter_option_changed(self, *_args):
        self._sc_update_pending_hint()

    def _sc_apply_filter(self, _text=None):
        self._sc_filter_dirty = False
        pattern = self._sc_filter_input.text().strip()
        self._sc_filter_applied_pattern = pattern
        self._sc_filter_applied_use_regex = self._sc_filter_regex_cb.isChecked()
        self._sc_filter_applied_case = self._sc_filter_case_cb.isChecked()
        self._sc_filter_applied_invert = self._sc_filter_invert_cb.isChecked()
        self._sc_filter_applied_before = self._sc_filter_before_spin.value()
        self._sc_filter_applied_after = self._sc_filter_after_spin.value()

        if not pattern:
            self._sc_filter_last_count = len(self._sc_all_logs)
            self._sc_rebuild_log_view()
            self._sc_filter_match_label.setText("")
            return

        use_regex = self._sc_filter_applied_use_regex
        case_sensitive = self._sc_filter_applied_case
        invert = self._sc_filter_applied_invert
        before = self._sc_filter_applied_before
        after = self._sc_filter_applied_after

        matched_indices = self._sc_get_matched_indices(
            pattern, use_regex, case_sensitive, invert
        )
        self._sc_filter_match_label.setText(f"Matched: {len(matched_indices)} lines")

        matched_set = set(matched_indices)
        visible = set()
        for idx in matched_indices:
            start = max(0, idx - before)
            end = min(len(self._sc_all_logs) - 1, idx + after)
            for i in range(start, end + 1):
                visible.add(i)

        self._sc_log_edit.setUpdatesEnabled(False)
        self._sc_log_edit.clear()
        cursor = self._sc_log_edit.textCursor()
        cursor.beginEditBlock()
        prev_shown = -2
        for i in sorted(visible):
            if before > 0 or after > 0:
                if prev_shown >= 0 and i - prev_shown > 1:
                    self._sc_log_edit.append(
                        f'<span style="color:{_CLR_TEXT_LINENO};">  ───</span>'
                    )
            if i in matched_set and not invert:
                self._sc_log_edit.append(
                    self._sc_html_with_filter_highlight(
                        self._sc_all_logs[i][1], pattern, use_regex, case_sensitive
                    )
                )
            else:
                self._sc_log_edit.append(self._sc_all_logs[i][1])
            prev_shown = i
        cursor.endEditBlock()
        self._sc_log_edit.setUpdatesEnabled(True)
        self._sc_filter_last_count = len(self._sc_all_logs)
        if self._sc_auto_scroll:
            self._sc_scroll_to_bottom()

    def _sc_rebuild_log_view(self):
        self._sc_log_edit.setUpdatesEnabled(False)
        self._sc_log_edit.clear()
        cursor = self._sc_log_edit.textCursor()
        cursor.beginEditBlock()
        for _raw, html in self._sc_all_logs:
            self._sc_log_edit.append(html)
        cursor.endEditBlock()
        self._sc_log_edit.setUpdatesEnabled(True)
        if self._sc_auto_scroll:
            self._sc_scroll_to_bottom()

    def _sc_is_filter_active(self):
        return (self._sc_filter_row.isVisible()
                and bool(self._sc_filter_applied_pattern))

    def _sc_get_matched_indices(self, pattern, use_regex, case_sensitive, invert):
        matched = []
        compiled = None
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(pattern, flags)
            except re.error:
                return matched

        for i, (raw, _html) in enumerate(self._sc_all_logs):
            if compiled is not None:
                hit = bool(compiled.search(raw))
            elif case_sensitive:
                hit = pattern in raw
            else:
                hit = pattern.lower() in raw.lower()
            if invert:
                hit = not hit
            if hit:
                matched.append(i)
        return matched

    @staticmethod
    def _sc_html_with_filter_highlight(html: str, pattern: str,
                                       use_regex: bool, case_sensitive: bool) -> str:
        if not pattern:
            return html

        compiled = None
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(pattern, flags)
            except re.error:
                return html
        else:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(re.escape(pattern), flags)
            except re.error:
                return html

        wrap_open = (
            f'<span style="background-color:{_CLR_FILTER_BG};'
            f'color:{_CLR_FILTER_TEXT};'
            f'border:1px solid {_CLR_FILTER_BORDER};'
            f'border-radius:2px;padding:0 1px;">'
        )
        wrap_close = '</span>'

        parts = re.split(r'(<[^>]*>)', html)
        for idx, seg in enumerate(parts):
            if not seg or seg.startswith('<'):
                continue
            try:
                parts[idx] = compiled.sub(
                    lambda m: f'{wrap_open}{m.group(0)}{wrap_close}', seg
                )
            except re.error:
                continue
        return ''.join(parts)

    def _sc_copy_logs(self):
        cb = QApplication.clipboard()
        if not cb:
            return
        lines = []
        if self._sc_is_filter_active():
            pattern = self._sc_filter_applied_pattern
            use_regex = self._sc_filter_applied_use_regex
            case_sensitive = self._sc_filter_applied_case
            invert = self._sc_filter_applied_invert
            before = self._sc_filter_applied_before
            after = self._sc_filter_applied_after
            matched_indices = self._sc_get_matched_indices(
                pattern, use_regex, case_sensitive, invert
            )
            visible = set()
            for idx in matched_indices:
                start = max(0, idx - before)
                end = min(len(self._sc_all_logs) - 1, idx + after)
                for i in range(start, end + 1):
                    visible.add(i)
            prev_shown = -2
            for i in sorted(visible):
                if (before > 0 or after > 0) and prev_shown >= 0 and i - prev_shown > 1:
                    lines.append("  ───")
                lines.append(self._sc_all_logs[i][0])
                prev_shown = i
        else:
            for raw, _html in self._sc_all_logs:
                lines.append(raw)
        cb.setText("\n".join(lines))

    def _sc_export_logs(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", f"serial_log_{ts}.txt", "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        temp_file = self._sc_log_temp_path
        if temp_file and os.path.isfile(temp_file):
            if self._sc_log_temp_handle is not None:
                try:
                    self._sc_log_temp_handle.flush()
                except OSError:
                    pass
            try:
                import shutil
                shutil.copy2(temp_file, path)
                return
            except OSError:
                pass
        with open(path, "w", encoding="utf-8") as f:
            for raw, _ in self._sc_all_logs:
                f.write(raw + "\n")

    @staticmethod
    def _sc_strip_timestamp(raw: str) -> str:
        return re.sub(r'^\d{2}:\d{2}:\d{2}\.\d{3}\s', '', raw)

    def _sc_on_save_toggle(self, checked: bool):
        if checked:
            if not self._sc_start_manual_save():
                self._sc_save_btn.setChecked(False)
        else:
            self._sc_stop_manual_save()

    def _sc_start_manual_save(self) -> bool:
        from ui.modules.serialCom_module.serialCom_module_frame import _SerialSaveDialog
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_dir = getattr(self, '_sc_log_save_path', '') or self._sc_fallback_dir()
        default_name = f"serial_log_{ts}.txt"
        dlg = _SerialSaveDialog(
            self,
            default_dir=default_dir,
            default_name=default_name,
            keep_timestamp=self._sc_save_keep_timestamp,
        )
        if dlg.exec() != QDialog.Accepted:
            return False
        cfg = dlg.get_config()
        save_dir = cfg["directory"]
        name = cfg["name"]
        keep_ts = cfg["keep_timestamp"]
        if not name:
            name = default_name
        if not name.lower().endswith(".txt"):
            name += ".txt"
        if not save_dir:
            save_dir = self._sc_fallback_dir()
        try:
            os.makedirs(save_dir, exist_ok=True)
        except OSError as exc:
            logger.error("Save: cannot create directory %s", save_dir, exc_info=True)
            QMessageBox.warning(self, "Save", f"Cannot create directory:\n{exc}")
            return False
        file_path = os.path.join(save_dir, name)
        if os.path.exists(file_path):
            reply = QMessageBox.question(
                self, "Save",
                f"File already exists:\n{file_path}\n\nOverwrite it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return False
        try:
            handle = open(file_path, "w", encoding="utf-8")
        except OSError as exc:
            logger.error("Save: cannot open file %s", file_path, exc_info=True)
            QMessageBox.warning(self, "Save", f"Cannot open file:\n{exc}")
            return False

        self._sc_save_keep_timestamp = keep_ts
        try:
            self._sc_write_buffer_to_handle(handle, keep_ts)
            handle.flush()
        except OSError:
            logger.error("Save: failed writing buffer to %s", file_path, exc_info=True)
            try:
                handle.close()
            except OSError:
                pass
            QMessageBox.warning(self, "Save", "Failed to write existing buffer.")
            return False

        self._sc_save_handle = handle
        self._sc_save_path = file_path
        self._sc_log_save_path = save_dir
        self._sc_append_system(f"[INFO] Save started: {file_path}", force_primary=True)
        return True

    def _sc_write_buffer_to_handle(self, handle, keep_ts: bool):
        written = False
        temp_file = self._sc_log_temp_path
        if temp_file and os.path.isfile(temp_file):
            if self._sc_log_temp_handle is not None:
                try:
                    self._sc_log_temp_handle.flush()
                except OSError:
                    pass
            try:
                with open(temp_file, "r", encoding="utf-8") as src:
                    for line in src:
                        line = line.rstrip("\n")
                        out = line if keep_ts else self._sc_strip_timestamp(line)
                        handle.write(out + "\n")
                written = True
            except OSError:
                written = False
        if not written:
            for raw, _ in self._sc_all_logs:
                out = raw if keep_ts else self._sc_strip_timestamp(raw)
                handle.write(out + "\n")

    def _sc_stop_manual_save(self):
        if self._sc_save_handle is not None:
            path = self._sc_save_path
            try:
                self._sc_save_handle.flush()
                self._sc_save_handle.close()
            except OSError:
                pass
            self._sc_save_handle = None
            if path:
                self._sc_append_system(f"[INFO] Save stopped: {path}", force_primary=True)
            self._sc_save_path = None

    def _sc_clear_logs(self):
        self._sc_all_logs.clear()
        self._sc_pending_html.clear()
        self._sc_log_edit.clear()
        self._sc_rx_bytes = 0
        self._sc_tx_bytes = 0
        self._sc_rx_line_buf = ""
        self._sc_status_rx_label.setText("RX: 0 B")
        self._sc_status_tx_label.setText("TX: 0 B")
        self._sc_filter_last_count = 0
        self._sc_filter_dirty = False
        self._sc_filter_match_label.setText("")
        self._sc_reset_applied_filter()
        self._sc_auto_scroll = True
        self._sc_scroll_lock_btn.setChecked(True)
        self._sc_start_temp_log()
        if self._sc_log_file_handle is not None and self._serial_connected:
            self._sc_stop_auto_save()
            self._sc_start_auto_save()

    def _sc_on_user_scroll(self, value):
        sb = self._sc_log_edit.verticalScrollBar()
        if sb and sb.maximum() > 0:
            at_bottom = value >= sb.maximum() - 5
            if not at_bottom and self._sc_auto_scroll:
                self._sc_auto_scroll = False
                self._sc_scroll_lock_btn.setChecked(False)
            elif at_bottom and not self._sc_auto_scroll:
                self._sc_auto_scroll = True
                self._sc_scroll_lock_btn.setChecked(True)

    def _sc_scroll_to_bottom(self):
        sb = self._sc_log_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())


