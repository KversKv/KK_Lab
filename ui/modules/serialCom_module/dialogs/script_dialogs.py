# -*- coding: utf-8 -*-
"""脚本编辑对话框：_SerialScriptStepDialog / _SerialScriptEditorDialog（原 serialCom_module_frame.py 拆出）。"""

import os

from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from ui.modules.serialCom_module.serial_style import (
    _CLR_SEND_BG,
    _CLR_TEXT_MUTED,
    _DLG_STYLE,
    _SVG_LOGS_DIR,
    _SVG_SERIAL_DIR,
    dialog_backdrop_style,
    dialog_cancel_button_style,
    dialog_line_edit_style,
    dialog_ok_button_style,
    script_editor_dialog_style,
)
from ui.modules.serialCom_module.widgets import _FramelessChromeDialog
from ui.modules.serialCom_module.controls.quick_cmd_controls import _QuickCommandPickerPopup

class _SerialScriptStepDialog(_FramelessChromeDialog):
    def __init__(self, parent=None, step: dict = None, mode: str = "create"):
        step = step or {}
        super().__init__(
            parent,
            title="ADD EXECUTION COMMAND" if mode == "create" else "EDIT STEP DIRECTIVE",
            icon_name="edit.svg",
        )
        self._apply_content_style(_DLG_STYLE)

        root = self._content
        root.setSpacing(14)

        card = QFrame()
        card.setObjectName("dlgGroupCard")
        form = QVBoxLayout(card)
        form.setContentsMargins(14, 12, 14, 12)
        form.setSpacing(8)

        cmd_lbl = QLabel("Step Command (TEXT/HEX payload)")
        cmd_lbl.setObjectName("dlgFieldLabel")
        form.addWidget(cmd_lbl)
        self._cmd_edit = QLineEdit(step.get("cmd", ""))
        self._cmd_edit.setPlaceholderText("e.g. AT+CWCAP")
        self._cmd_edit.setStyleSheet(dialog_line_edit_style())
        form.addWidget(self._cmd_edit)

        pw_row = QHBoxLayout()
        pw_row.setSpacing(8)
        prio_box = QVBoxLayout()
        prio_box.setSpacing(4)
        prio_lbl = QLabel("Priority Ordering")
        prio_lbl.setObjectName("dlgFieldLabel")
        prio_box.addWidget(prio_lbl)
        self._prio_spin = QSpinBox()
        self._prio_spin.setRange(1, 99999)
        self._prio_spin.setValue(int(step.get("priority", 1)) or 1)
        prio_box.addWidget(self._prio_spin)
        pw_row.addLayout(prio_box, 1)

        wait_box = QVBoxLayout()
        wait_box.setSpacing(4)
        wait_lbl = QLabel("Step Wait Delay (ms)")
        wait_lbl.setObjectName("dlgFieldLabel")
        wait_box.addWidget(wait_lbl)
        self._wait_spin = QSpinBox()
        self._wait_spin.setRange(0, 999999)
        self._wait_spin.setValue(int(step.get("wait_ms", 0)))
        wait_box.addWidget(self._wait_spin)
        pw_row.addLayout(wait_box, 1)
        form.addLayout(pw_row)

        kw_lbl = QLabel("Expected Wait Keyword (Optional)")
        kw_lbl.setObjectName("dlgFieldLabel")
        form.addWidget(kw_lbl)
        self._kw_edit = QLineEdit(step.get("wait_keyword", ""))
        self._kw_edit.setPlaceholderText("e.g. OK, READY, or SUCCESS")
        self._kw_edit.setStyleSheet(dialog_line_edit_style())
        form.addWidget(self._kw_edit)

        to_lbl = QLabel("Keyword Timeout (ms - default is Wait Delay)")
        to_lbl.setObjectName("dlgFieldLabel")
        form.addWidget(to_lbl)
        self._to_spin = QSpinBox()
        self._to_spin.setRange(0, 999999)
        self._to_spin.setValue(int(step.get("wait_timeout_ms", 0)))
        form.addWidget(self._to_spin)
        root.addWidget(card)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(dialog_cancel_button_style())
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(488)

    def _on_accept(self):
        if not self._cmd_edit.text().strip():
            QMessageBox.warning(self, "提示", "指令不能为空")
            return
        self.accept()

    def result_step(self) -> dict:
        return {
            "cmd": self._cmd_edit.text().strip(),
            "priority": int(self._prio_spin.value()),
            "wait_ms": int(self._wait_spin.value()),
            "wait_keyword": self._kw_edit.text().strip(),
            "wait_timeout_ms": int(self._to_spin.value()),
        }


class _SerialScriptEditorDialog(QDialog):
    _COLS = ["#", "COMMAND PAYLOAD", "WAIT (MS)", "WAIT KEYWORD", "TIMEOUT (MS)", "ACTIONS"]

    def __init__(self, parent=None, script: dict = None, quick_commands: list = None):
        super().__init__(parent)
        self.setWindowTitle("脚本编辑器")
        self.setObjectName("scEditorDialog")
        self.setMinimumSize(1008, 672)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet(_DLG_STYLE + script_editor_dialog_style())
        script = script or {}
        self._quick_commands = list(quick_commands or [])
        self._drag_pos = None
        self._backdrop = None
        self._blur_effect = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(54, 50, 54, 62)
        outer.setSpacing(0)

        container = QFrame()
        container.setObjectName("scEditorContainer")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(15, 23, 42, 50))
        container.setGraphicsEffect(shadow)
        outer.addWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- 标题栏 ---
        header = QFrame()
        header.setObjectName("scEditorHeader")
        header.installEventFilter(self)
        self._header = header
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(24, 16, 20, 16)
        header_row.setSpacing(10)
        title_icon = QLabel()
        _ico = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "edit.svg"), _CLR_SEND_BG, 18)
        if not _ico.isNull():
            title_icon.setPixmap(_ico.pixmap(18, 18))
        header_row.addWidget(title_icon)
        title = QLabel("EDIT SUITE & SEQUENCE STEPS")
        title.setObjectName("scEditorTitle")
        header_row.addWidget(title)
        header_row.addStretch()
        close_btn = QPushButton("\u2715")
        close_btn.setObjectName("scEditorClose")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(28, 28)
        close_btn.setAutoDefault(False)
        close_btn.setDefault(False)
        close_btn.clicked.connect(self.reject)
        header_row.addWidget(close_btn)
        root.addWidget(header)

        body = QVBoxLayout()
        body.setContentsMargins(24, 18, 24, 4)
        body.setSpacing(16)

        # --- SUITE NAME 卡片 ---
        prop_card = QFrame()
        prop_card.setObjectName("scEditorCard")
        prop_form = QVBoxLayout(prop_card)
        prop_form.setContentsMargins(20, 16, 20, 16)
        prop_form.setSpacing(8)

        name_lbl = QLabel("SUITE NAME")
        name_lbl.setObjectName("scEditorFieldLabel")
        prop_form.addWidget(name_lbl)

        prop_row = QHBoxLayout()
        prop_row.setSpacing(16)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("e.g. ESP32 WiFi Handshake Suite")
        self._name_edit.setText(script.get("name", ""))
        self._name_edit.setMinimumWidth(260)
        prop_row.addWidget(self._name_edit, 0)

        self._loop_cb = QCheckBox("Loop Sequence Execution")
        self._loop_cb.setChecked(bool(script.get("loop", False)))
        prop_row.addWidget(self._loop_cb)

        count_lbl = QLabel("Count")
        count_lbl.setObjectName("scEditorInlineLabel")
        prop_row.addWidget(count_lbl)
        self._loop_spin = QSpinBox()
        self._loop_spin.setRange(1, 99999)
        self._loop_spin.setValue(int(script.get("loop_count", 1)) or 1)
        self._loop_spin.setFixedWidth(78)
        prop_row.addWidget(self._loop_spin)

        self._loop_inf_cb = QCheckBox("\u221e")
        self._loop_inf_cb.setChecked(bool(script.get("loop_infinite", False)))
        self._loop_inf_cb.setToolTip("Loop forever until manually stopped")
        prop_row.addWidget(self._loop_inf_cb)

        self._loop_cb.toggled.connect(self._sync_loop_widgets)
        self._loop_inf_cb.toggled.connect(self._sync_loop_widgets)
        self._sync_loop_widgets()
        prop_row.addStretch()
        prop_form.addLayout(prop_row)
        body.addWidget(prop_card)

        # --- 步骤区标题 + Add Step ---
        steps_head = QHBoxLayout()
        steps_head.setSpacing(8)
        self._steps_title = QLabel("Sequence Directives (0)")
        self._steps_title.setObjectName("scEditorSectionTitle")
        steps_head.addWidget(self._steps_title)
        steps_head.addStretch()

        add_btn = QPushButton("  Add Step")
        add_btn.setObjectName("scEditorAddBtn")
        add_btn.setCursor(Qt.PointingHandCursor)
        _plus_icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "plus.svg"), _CLR_SEND_BG, 12)
        if not _plus_icon.isNull():
            add_btn.setIcon(_plus_icon)
        add_btn.setAutoDefault(False)
        add_btn.setDefault(False)
        add_btn.clicked.connect(lambda: self._add_row())
        steps_head.addWidget(add_btn)
        body.addLayout(steps_head)

        # --- 步骤表 ---
        self._table = QTableWidget(0, len(self._COLS))
        self._table.setObjectName("dlgStepTable")
        self._table.setHorizontalHeaderLabels(self._COLS)
        _kw_header_item = self._table.horizontalHeaderItem(3)
        if _kw_header_item is not None:
            _kw_header_item.setForeground(QColor("#9898ed"))
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)
        self._table.setWordWrap(False)
        self._table.setFocusPolicy(Qt.NoFocus)
        self._table.verticalHeader().setDefaultSectionSize(52)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        hdr = self._table.horizontalHeader()
        hdr.setMinimumSectionSize(64)
        hdr.setHighlightSections(False)
        hdr.setSectionResizeMode(0, QHeaderView.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        for c in (2, 3, 4, 5):
            hdr.setSectionResizeMode(c, QHeaderView.Fixed)
        self._table.setColumnWidth(0, 48)
        self._table.setColumnWidth(2, 110)
        self._table.setColumnWidth(3, 150)
        self._table.setColumnWidth(4, 120)
        self._table.setColumnWidth(5, 110)
        body.addWidget(self._table, 1)

        root.addLayout(body, 1)

        for step in script.get("steps", []):
            self._add_row(step)
        if self._table.rowCount() == 0:
            self._add_row()
        self._refresh_index_column()

        # --- 底部 Cancel / Save ---
        footer = QFrame()
        footer.setObjectName("scEditorFooter")
        btn_row = QHBoxLayout(footer)
        btn_row.setContentsMargins(24, 14, 24, 16)
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("scEditorCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Save Suite Configuration")
        ok_btn.setObjectName("scEditorSaveBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(ok_btn)
        root.addWidget(footer)

        self._script_id = script.get("id", "")

    def _target_window(self):
        parent = self.parent()
        if parent is None:
            return None
        return parent.window()

    def _install_backdrop(self):
        win = self._target_window()
        if win is None:
            return
        try:
            blur = QGraphicsBlurEffect(win)
            blur.setBlurRadius(9)
            win.setGraphicsEffect(blur)
            self._blur_effect = blur
        except Exception:
            self._blur_effect = None
        backdrop = QWidget(win)
        backdrop.setObjectName("scEditorBackdrop")
        backdrop.setStyleSheet(dialog_backdrop_style())
        backdrop.setGeometry(win.rect())
        backdrop.show()
        backdrop.raise_()
        self._backdrop = backdrop

    def _remove_backdrop(self):
        if self._backdrop is not None:
            self._backdrop.deleteLater()
            self._backdrop = None
        win = self._target_window()
        if win is not None:
            win.setGraphicsEffect(None)
        self._blur_effect = None

    def exec(self):
        self._install_backdrop()
        try:
            return super().exec()
        finally:
            self._remove_backdrop()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent  # 局部引入，避免顶部冗余导入
        if obj is getattr(self, "_header", None):
            et = event.type()
            if et == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if et == QEvent.MouseMove and self._drag_pos is not None and (event.buttons() & Qt.LeftButton):
                self.move(event.globalPosition().toPoint() - self._drag_pos)
                return True
            if et == QEvent.MouseButtonRelease:
                self._drag_pos = None
        return super().eventFilter(obj, event)

    def _wrap_cell(self, widget) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignVCenter)
        lay.addWidget(widget, 0, Qt.AlignVCenter)
        return holder

    def _make_cmd_cell(self, text: str) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(6)
        lay.setAlignment(Qt.AlignVCenter)
        edit = QLineEdit(text)
        edit.setPlaceholderText("如：AT+RST")
        holder._cmd_edit = edit
        lay.addWidget(edit, 1, Qt.AlignVCenter)
        pick_btn = QPushButton("选择")
        pick_btn.setObjectName("dlgRowBtn")
        pick_btn.setCursor(Qt.PointingHandCursor)
        pick_btn.setToolTip("从 Quick Commands 选择指令")
        pick_btn.clicked.connect(lambda: self._pick_quick_command(holder, pick_btn))
        if not self._quick_commands:
            pick_btn.setEnabled(False)
            pick_btn.setToolTip("暂无可选的 Quick Commands")
        lay.addWidget(pick_btn)
        return holder

    def _pick_quick_command(self, holder, anchor=None):
        if not self._quick_commands:
            return

        def _on_pick(entry):
            edit = getattr(holder, "_cmd_edit", None)
            if isinstance(edit, QLineEdit):
                edit.setText(entry.get("content", ""))

        popup = _QuickCommandPickerPopup(self, self._quick_commands, _on_pick)
        popup.popup_at(anchor)

    def _make_index_cell(self, row: int) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignCenter)
        lbl = QLabel(str(row + 1))
        lbl.setObjectName("scEditorRowIndex")
        lbl.setAlignment(Qt.AlignCenter)
        holder._index_label = lbl
        lay.addWidget(lbl)
        return holder

    def _make_keyword_cell(self, text: str) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignVCenter)
        edit = QLineEdit(text)
        edit.setPlaceholderText("如：OK")
        holder._kw_edit = edit
        lay.addWidget(edit, 1, Qt.AlignVCenter)
        return holder

    def _make_actions_cell(self, row: int) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignCenter)

        def _icon_btn(svg_name: str, tip: str, slot):
            btn = QPushButton()
            btn.setObjectName("scEditorRowIcon")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(28, 28)
            btn.setToolTip(tip)
            btn.setAutoDefault(False)
            btn.setDefault(False)
            ico = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, svg_name), _CLR_TEXT_MUTED, 15)
            if not ico.isNull():
                btn.setIcon(ico)
            btn.clicked.connect(slot)
            return btn

        up_btn = _icon_btn("arrow-up.svg", "上移", lambda: self._move_holder(holder, -1))
        down_btn = _icon_btn("arrow-down.svg", "下移", lambda: self._move_holder(holder, 1))
        del_btn = _icon_btn("trash.svg", "删除", lambda: self._del_holder(holder))
        lay.addWidget(up_btn)
        lay.addWidget(down_btn)
        lay.addWidget(del_btn)
        return holder

    def _add_row(self, step: dict = None):
        step = step or {
            "cmd": "", "priority": self._table.rowCount() + 1, "wait_ms": 1000,
            "wait_keyword": "", "wait_timeout_ms": 0,
        }
        row = self._table.rowCount()
        self._table.insertRow(row)

        index_cell = self._make_index_cell(row)
        # 原步骤字典随行携带：编辑器无对应列的扩展键（send_type/line_ending）在收集时带回
        index_cell.setProperty("_orig_step", dict(step))
        self._table.setCellWidget(row, 0, index_cell)
        self._table.setCellWidget(row, 1, self._make_cmd_cell(step.get("cmd", "")))

        wait_spin = QSpinBox()
        wait_spin.setRange(0, 3600000)
        wait_spin.setSingleStep(100)
        wait_spin.setValue(int(step.get("wait_ms", 1000)))
        self._table.setCellWidget(row, 2, self._wrap_cell(wait_spin))

        self._table.setCellWidget(row, 3, self._make_keyword_cell(step.get("wait_keyword", "")))

        to_spin = QSpinBox()
        to_spin.setRange(0, 3600000)
        to_spin.setSingleStep(100)
        to_spin.setValue(int(step.get("wait_timeout_ms", 0)))
        self._table.setCellWidget(row, 4, self._wrap_cell(to_spin))

        self._table.setCellWidget(row, 5, self._make_actions_cell(row))
        self._refresh_index_column()

    def _refresh_index_column(self):
        count = self._table.rowCount()
        for row in range(count):
            holder = self._table.cellWidget(row, 0)
            lbl = getattr(holder, "_index_label", None) if holder else None
            if isinstance(lbl, QLabel):
                lbl.setText(str(row + 1))
        self._steps_title.setText(f"Sequence Directives ({count})")

    def _row_of_holder(self, holder) -> int:
        for row in range(self._table.rowCount()):
            for col in range(self._table.columnCount()):
                if self._table.cellWidget(row, col) is holder:
                    return row
        return -1

    def _move_holder(self, holder, delta: int):
        row = self._row_of_holder(holder)
        if row < 0:
            return
        self._table.setCurrentCell(row, 1)
        self._move_row(delta)

    def _del_holder(self, holder):
        row = self._row_of_holder(holder)
        if row < 0:
            return
        self._table.removeRow(row)
        self._refresh_index_column()

    def _del_row(self):
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)

    def _move_row(self, delta: int):
        row = self._table.currentRow()
        if row < 0:
            return
        target = row + delta
        if target < 0 or target >= self._table.rowCount():
            return
        steps = self._collect_steps()
        steps[row], steps[target] = steps[target], steps[row]
        self._reload_steps(steps)
        self._table.setCurrentCell(target, 1)

    def _inner_widget(self, row: int, col: int):
        holder = self._table.cellWidget(row, col)
        if holder is None:
            return None
        lay = holder.layout()
        if lay is not None and lay.count() > 0:
            return lay.itemAt(0).widget()
        return holder

    def _renumber_priority(self):
        self._refresh_index_column()

    def _reload_steps(self, steps: list):
        self._table.setRowCount(0)
        for step in steps:
            self._add_row(step)
        self._refresh_index_column()

    def _collect_steps(self) -> list:
        steps = []
        for row in range(self._table.rowCount()):
            cmd_holder = self._table.cellWidget(row, 1)
            cmd_edit = getattr(cmd_holder, "_cmd_edit", None) if cmd_holder else None
            kw_holder = self._table.cellWidget(row, 3)
            kw_edit = getattr(kw_holder, "_kw_edit", None) if kw_holder else None
            wait = self._inner_widget(row, 2)
            to = self._inner_widget(row, 4)
            step_dict = {
                "cmd": cmd_edit.text() if isinstance(cmd_edit, QLineEdit) else "",
                "priority": row + 1,
                "wait_ms": wait.value() if isinstance(wait, QSpinBox) else 0,
                "wait_keyword": kw_edit.text() if isinstance(kw_edit, QLineEdit) else "",
                "wait_timeout_ms": to.value() if isinstance(to, QSpinBox) else 0,
            }
            index_holder = self._table.cellWidget(row, 0)
            orig = index_holder.property("_orig_step") if index_holder else None
            if isinstance(orig, dict):
                for k in ("send_type", "line_ending"):
                    if k in orig:
                        step_dict[k] = orig[k]
            steps.append(step_dict)
        return steps

    def _on_accept(self):
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写脚本名称")
            return
        steps = [s for s in self._collect_steps() if s["cmd"].strip()]
        if not steps:
            QMessageBox.warning(self, "提示", "至少需要一个有内容的步骤")
            return
        self.accept()

    def _sync_loop_widgets(self, *args):
        loop_on = self._loop_cb.isChecked()
        loop_inf = self._loop_inf_cb.isChecked()
        self._loop_inf_cb.setEnabled(loop_on)
        self._loop_spin.setEnabled(loop_on and not loop_inf)

    def get_script(self) -> dict:
        return {
            "id": self._script_id,
            "name": self._name_edit.text().strip(),
            "loop": self._loop_cb.isChecked(),
            "loop_count": self._loop_spin.value(),
            "loop_infinite": self._loop_cb.isChecked() and self._loop_inf_cb.isChecked(),
            "steps": [s for s in self._collect_steps() if s["cmd"].strip()],
        }
