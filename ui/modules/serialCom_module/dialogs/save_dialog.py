# -*- coding: utf-8 -*-
"""_SerialSaveDialog — 串口日志保存对话框（原 serialCom_module_frame.py 拆出）。"""

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)
from PySide6.QtCore import Qt
from ui.modules.serialCom_module.widgets import _FramelessChromeDialog
from ui.modules.serialCom_module.serial_style import (
    dialog_cancel_button_style,
    dialog_ok_button_style,
    quick_cmd_dialog_style,
)

class _SerialSaveDialog(_FramelessChromeDialog):

    def __init__(self, parent=None, default_dir="", default_name="", keep_timestamp=True):
        super().__init__(parent, title="SAVE LOGS", icon_name="edit.svg")
        self._apply_content_style(quick_cmd_dialog_style())

        root = self._content
        root.setSpacing(10)

        root.addWidget(QLabel("保存位置"))
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self._dir_edit = QLineEdit()
        self._dir_edit.setPlaceholderText("选择保存目录")
        self._dir_edit.setText(default_dir)
        dir_row.addWidget(self._dir_edit, 1)
        browse_btn = QPushButton("浏览…")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(dialog_cancel_button_style())
        browse_btn.setAutoDefault(False)
        browse_btn.setDefault(False)
        browse_btn.clicked.connect(self._on_browse)
        dir_row.addWidget(browse_btn)
        root.addLayout(dir_row)

        root.addWidget(QLabel("文件名"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如:serial_log.txt")
        self._name_edit.setText(default_name)
        root.addWidget(self._name_edit)

        self._keep_ts_cb = QCheckBox("保留系统时间戳（每行前缀 HH:MM:SS.fff）")
        self._keep_ts_cb.setChecked(keep_timestamp)
        root.addWidget(self._keep_ts_cb)

        hint = QLabel("点击保存后将写入当前完整日志，并持续追加后续新日志。")
        hint.setWordWrap(True)
        root.addWidget(hint)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(dialog_cancel_button_style())
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Save")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(548)

    def _on_browse(self):
        current = self._dir_edit.text().strip()
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", current)
        if directory:
            self._dir_edit.setText(directory)

    def get_config(self) -> dict:
        return {
            "directory": self._dir_edit.text().strip(),
            "name": self._name_edit.text().strip(),
            "keep_timestamp": self._keep_ts_cb.isChecked(),
        }
