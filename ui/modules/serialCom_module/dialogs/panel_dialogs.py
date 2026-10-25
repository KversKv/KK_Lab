# -*- coding: utf-8 -*-
"""日志面板相关对话框：_AddLogPanelDialog / _PanelSettingsDialog（原 serialCom_module_frame.py 拆出）。"""

from PySide6.QtWidgets import (
    QCheckBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)
from PySide6.QtCore import Qt
from debug_config import DEBUG_MOCK
from core.serial_io.serial_backend import list_serial_ports
from ui.modules.serialCom_module.serial_style import (
    SerialDarkComboBox,
    _DLG_STYLE,
    add_serial_port_item,
    dialog_line_edit_style,
)
from ui.modules.serialCom_module.widgets import _FramelessChromeDialog

class _AddLogPanelDialog(_FramelessChromeDialog):

    def __init__(self, panel_index: int = 2, parent=None):
        super().__init__(parent, title="ADD LOG PANEL", icon_name="plus.svg")
        self._panel_index = panel_index
        self._apply_content_style(_DLG_STYLE)

        root = self._content
        root.setSpacing(12)

        title = QLabel("New Serial LOG")
        title.setObjectName("dlgSectionTitle")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Panel Name"), 0, 0)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g. LOG-2")
        self._title_edit.setText(f"Serial Log {self._panel_index}")
        self._title_edit.setStyleSheet(dialog_line_edit_style())
        grid.addWidget(self._title_edit, 0, 1)

        grid.addWidget(QLabel("Port"), 1, 0)
        self._port_combo = SerialDarkComboBox()
        self._port_combo.setFixedHeight(26)
        self._port_combo.setEditable(True)
        try:
            ports = list_serial_ports()
            for p in ports:
                add_serial_port_item(self._port_combo, f"{p.device} - {p.description}")
        except Exception:
            pass
        if self._port_combo.count() == 0:
            if DEBUG_MOCK:
                self._port_combo.addItem("[MOCK] COM99 - Mock Serial Device")
            else:
                self._port_combo.addItem("No serial ports found")
        grid.addWidget(self._port_combo, 1, 1)

        grid.addWidget(QLabel("Baudrate"), 2, 0)
        self._baud_combo = SerialDarkComboBox()
        self._baud_combo.setFixedHeight(26)
        self._baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000"]:
            self._baud_combo.addItem(br)
        self._baud_combo.setCurrentIndex(0)
        grid.addWidget(self._baud_combo, 2, 1)

        grid.addWidget(QLabel("Data bits"), 3, 0)
        self._databit_combo = SerialDarkComboBox()
        self._databit_combo.setFixedHeight(26)
        for d in ["8", "7", "6", "5"]:
            self._databit_combo.addItem(d)
        grid.addWidget(self._databit_combo, 3, 1)

        grid.addWidget(QLabel("Stop bits"), 4, 0)
        self._stopbit_combo = SerialDarkComboBox()
        self._stopbit_combo.setFixedHeight(26)
        for s in ["1", "1.5", "2"]:
            self._stopbit_combo.addItem(s)
        grid.addWidget(self._stopbit_combo, 4, 1)

        grid.addWidget(QLabel("Parity"), 5, 0)
        self._parity_combo = SerialDarkComboBox()
        self._parity_combo.setFixedHeight(26)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._parity_combo.addItem(p)
        grid.addWidget(self._parity_combo, 5, 1)

        grid.addWidget(QLabel("Flow Control"), 6, 0)
        self._flow_combo = SerialDarkComboBox()
        self._flow_combo.setFixedHeight(26)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._flow_combo.addItem(fc)
        grid.addWidget(self._flow_combo, 6, 1)

        root.addLayout(grid)

        mode_grp = QHBoxLayout()
        mode_grp.setSpacing(16)
        mode_label = QLabel("Open in:")
        mode_grp.addWidget(mode_label)
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        self._mode_same_window = QRadioButton("Same Window")
        self._mode_same_window.setChecked(True)
        self._mode_independent = QRadioButton("Independent Window")
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._mode_same_window, 0)
        self._mode_group.addButton(self._mode_independent, 1)
        mode_grp.addWidget(self._mode_same_window)
        mode_grp.addWidget(self._mode_independent)
        mode_grp.addStretch()
        root.addLayout(mode_grp)

        self._auto_connect_cb = QCheckBox("Auto connect after creation")
        self._auto_connect_cb.setChecked(True)
        root.addWidget(self._auto_connect_cb)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dlgCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("dlgOkBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(508)

    def get_config(self):
        port_text = self._port_combo.currentText()
        port = port_text.split()[0] if port_text and not port_text.startswith("No ") else ""
        try:
            baudrate = int(self._baud_combo.currentText().strip())
        except ValueError:
            baudrate = 115200
        return {
            "title": self._title_edit.text().strip() or "Serial Log",
            "port": port,
            "baudrate": baudrate,
            "databit": int(self._databit_combo.currentText()),
            "stopbit": self._stopbit_combo.currentText(),
            "parity": self._parity_combo.currentText(),
            "flow": self._flow_combo.currentText(),
            "auto_connect": self._auto_connect_cb.isChecked(),
            "independent_window": self._mode_independent.isChecked(),
        }


class _PanelSettingsDialog(_FramelessChromeDialog):

    def __init__(self, current_config: dict, parent=None, name_only: bool = False):
        super().__init__(parent, title="PANEL SETTINGS", icon_name="settings.svg")
        self._apply_content_style(_DLG_STYLE)

        root = self._content
        root.setSpacing(12)

        title = QLabel("Rename Panel" if name_only else "Serial Port Settings")
        title.setObjectName("dlgSectionTitle")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Panel Name"), 0, 0)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g. LOG-2")
        self._title_edit.setText(current_config.get("title", "Serial Log"))
        self._title_edit.setStyleSheet(dialog_line_edit_style())
        grid.addWidget(self._title_edit, 0, 1)

        grid.addWidget(QLabel("Port"), 1, 0)
        self._port_combo = SerialDarkComboBox()
        self._port_combo.setFixedHeight(26)
        self._port_combo.setEditable(True)
        try:
            ports = list_serial_ports()
            for p in ports:
                add_serial_port_item(self._port_combo, f"{p.device} - {p.description}")
        except Exception:
            pass
        if self._port_combo.count() == 0:
            if DEBUG_MOCK:
                self._port_combo.addItem("[MOCK] COM99 - Mock Serial Device")
            else:
                self._port_combo.addItem("No serial ports found")
        cur_port = current_config.get("port", "")
        if cur_port:
            for i in range(self._port_combo.count()):
                if self._port_combo.itemText(i).startswith(cur_port):
                    self._port_combo.setCurrentIndex(i)
                    break
            else:
                self._port_combo.setEditText(cur_port)
        grid.addWidget(self._port_combo, 1, 1)

        grid.addWidget(QLabel("Baudrate"), 2, 0)
        self._baud_combo = SerialDarkComboBox()
        self._baud_combo.setFixedHeight(26)
        self._baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000", "115200", "9600"]:
            self._baud_combo.addItem(br)
        cur_baud = str(current_config.get("baudrate", 921600))
        idx = self._baud_combo.findText(cur_baud)
        if idx >= 0:
            self._baud_combo.setCurrentIndex(idx)
        else:
            self._baud_combo.setEditText(cur_baud)
        grid.addWidget(self._baud_combo, 2, 1)

        grid.addWidget(QLabel("Data bits"), 3, 0)
        self._databit_combo = SerialDarkComboBox()
        self._databit_combo.setFixedHeight(26)
        for d in ["8", "7", "6", "5"]:
            self._databit_combo.addItem(d)
        cur_databit = str(current_config.get("databit", 8))
        idx = self._databit_combo.findText(cur_databit)
        if idx >= 0:
            self._databit_combo.setCurrentIndex(idx)
        grid.addWidget(self._databit_combo, 3, 1)

        grid.addWidget(QLabel("Stop bits"), 4, 0)
        self._stopbit_combo = SerialDarkComboBox()
        self._stopbit_combo.setFixedHeight(26)
        for s in ["1", "1.5", "2"]:
            self._stopbit_combo.addItem(s)
        cur_stopbit = str(current_config.get("stopbit", "1"))
        idx = self._stopbit_combo.findText(cur_stopbit)
        if idx >= 0:
            self._stopbit_combo.setCurrentIndex(idx)
        grid.addWidget(self._stopbit_combo, 4, 1)

        grid.addWidget(QLabel("Parity"), 5, 0)
        self._parity_combo = SerialDarkComboBox()
        self._parity_combo.setFixedHeight(26)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._parity_combo.addItem(p)
        cur_parity = current_config.get("parity", "None")
        idx = self._parity_combo.findText(cur_parity)
        if idx >= 0:
            self._parity_combo.setCurrentIndex(idx)
        grid.addWidget(self._parity_combo, 5, 1)

        grid.addWidget(QLabel("Flow Control"), 6, 0)
        self._flow_combo = SerialDarkComboBox()
        self._flow_combo.setFixedHeight(26)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._flow_combo.addItem(fc)
        cur_flow = current_config.get("flow", "None")
        idx = self._flow_combo.findText(cur_flow)
        if idx >= 0:
            self._flow_combo.setCurrentIndex(idx)
        grid.addWidget(self._flow_combo, 6, 1)

        root.addLayout(grid)
        if name_only:
            for row in range(1, 7):
                for col in range(2):
                    item = grid.itemAtPosition(row, col)
                    if item is not None and item.widget() is not None:
                        item.widget().setVisible(False)

        self._auto_connect_cb = QCheckBox("Auto connect after apply")
        self._auto_connect_cb.setChecked(True)
        self._auto_connect_cb.setVisible(not name_only)
        root.addWidget(self._auto_connect_cb)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dlgCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Apply")
        ok_btn.setObjectName("dlgOkBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self.setFixedWidth(508)

    def get_config(self):
        port_text = self._port_combo.currentText()
        port = port_text.split()[0] if port_text and not port_text.startswith("No ") else ""
        try:
            baudrate = int(self._baud_combo.currentText().strip())
        except ValueError:
            baudrate = 115200
        return {
            "title": self._title_edit.text().strip() or "Serial Log",
            "port": port,
            "baudrate": baudrate,
            "databit": int(self._databit_combo.currentText()),
            "stopbit": self._stopbit_combo.currentText(),
            "parity": self._parity_combo.currentText(),
            "flow": self._flow_combo.currentText(),
            "auto_connect": self._auto_connect_cb.isChecked(),
        }
