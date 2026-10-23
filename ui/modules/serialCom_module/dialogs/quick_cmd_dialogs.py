# -*- coding: utf-8 -*-
"""快捷命令对话框：_QuickTextInputDialog / _QuickCmdDialog（原 serialCom_module_frame.py 拆出）。"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
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

class _QuickTextInputDialog(_FramelessChromeDialog):

    def __init__(self, parent=None, title="", label="", text="",
                 placeholder="", ok_text="OK"):
        super().__init__(parent, title=(title or "").upper(), icon_name="edit.svg")
        self._apply_content_style(quick_cmd_dialog_style())

        root = self._content
        root.setSpacing(10)

        if label:
            root.addWidget(QLabel(label))

        self._edit = QLineEdit()
        self._edit.setText(text)
        if placeholder:
            self._edit.setPlaceholderText(placeholder)
        self._edit.selectAll()
        self._edit.returnPressed.connect(self.accept)
        root.addWidget(self._edit)

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

        ok_btn = QPushButton(ok_text)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(468)
        self._edit.setFocus()

    def get_text(self) -> str:
        return self._edit.text().strip()

    @staticmethod
    def get_input(parent=None, title="", label="", text="",
                  placeholder="", ok_text="OK"):
        dlg = _QuickTextInputDialog(
            parent=parent, title=title, label=label, text=text,
            placeholder=placeholder, ok_text=ok_text,
        )
        accepted = dlg.exec() == QDialog.Accepted
        return dlg.get_text(), accepted


class _QuickCmdDialog(_FramelessChromeDialog):

    def __init__(self, parent=None, name="", content="", send_type="text",
                 line_ending="\r\n", encoding="ascii"):
        is_edit = bool(name or content)
        super().__init__(
            parent,
            title="EDIT QUICK COMMAND" if is_edit else "NEW QUICK COMMAND",
            icon_name="edit.svg",
        )
        self._apply_content_style(quick_cmd_dialog_style())

        root = self._content
        root.setSpacing(10)

        root.addWidget(QLabel("指令名称"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如:查询版本")
        self._name_edit.setText(name)
        root.addWidget(self._name_edit)

        root.addWidget(QLabel("指令内容"))
        self._cmd_edit = QLineEdit()
        self._cmd_edit.setPlaceholderText("如:AT+GMR")
        self._cmd_edit.setText(content)
        root.addWidget(self._cmd_edit)

        root.addWidget(QLabel("发送方式"))
        self._send_type_combo = QComboBox()
        # 显示文案大写（TEXT / HEX），userData 保持小写以兼容旧数据
        self._send_type_combo.addItem("TEXT", "text")
        self._send_type_combo.addItem("HEX", "hex")
        idx = self._send_type_combo.findData(send_type)
        self._send_type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        root.addWidget(self._send_type_combo)

        root.addWidget(QLabel("结尾符"))
        self._line_ending_combo = QComboBox()
        self._line_ending_combo.addItem("无", "")
        self._line_ending_combo.addItem("\\r", "\r")
        self._line_ending_combo.addItem("\\n", "\n")
        self._line_ending_combo.addItem("\\r\\n", "\r\n")
        idx = self._line_ending_combo.findData(line_ending)
        self._line_ending_combo.setCurrentIndex(idx if idx >= 0 else 3)
        root.addWidget(self._line_ending_combo)

        root.addWidget(QLabel("编码"))
        self._encoding_combo = QComboBox()
        # 默认 ascii，放在第一位以便 setCurrentIndex(0) 兜底命中
        # 显示文案大写（ASCII / UTF-8 / GBK），userData 保持小写以兼容旧数据
        for enc_label, enc_value in (("ASCII", "ascii"), ("UTF-8", "utf-8"), ("GBK", "gbk")):
            self._encoding_combo.addItem(enc_label, enc_value)
        idx = self._encoding_combo.findData(encoding)
        self._encoding_combo.setCurrentIndex(idx if idx >= 0 else 0)
        root.addWidget(self._encoding_combo)

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

        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(488)

    def get_command(self) -> dict:
        return {
            "name": self._name_edit.text().strip(),
            "content": self._cmd_edit.text(),
            "send_type": self._send_type_combo.currentData() or "text",
            "line_ending": self._line_ending_combo.currentData() or "",
            "encoding": self._encoding_combo.currentData() or "ascii",
        }

    # 兼容老调用 (已无人使用)
    def get_name(self):
        return self._name_edit.text().strip()

    def get_cmd(self):
        return self._cmd_edit.text().strip()
