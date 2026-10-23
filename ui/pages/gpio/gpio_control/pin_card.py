# -*- coding: utf-8 -*-
"""Pin Matrix 引脚卡片控件（BIT + 名称 + 别名 + 方向/电平/上下拉 + LED）。"""

from PySide6.QtWidgets import (
    QHBoxLayout, QPushButton, QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt

class _PinCard(QFrame):
    """Pin Matrix 单行引脚条：BIT + 名称 + 别名 + OUT/IN、电平、PU/PD + LED。"""

    def __init__(self, group, pin, on_select, on_dir, on_level, on_pull,
                 on_menu, parent=None):
        super().__init__(parent)
        self.group = group
        self.pin = pin
        self._on_select = on_select
        self._on_menu = on_menu
        self.setObjectName("pinCard")
        self.setProperty("sel", "0")
        self.setProperty("lvl", "x")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 1, 6, 1)
        lay.setSpacing(6)

        self.bit_label = QLabel("BIT--")
        self.bit_label.setObjectName("pinBit")
        self.bit_label.setFixedWidth(38)
        lay.addWidget(self.bit_label)

        self.name_label = QLabel("GPIO--")
        self.name_label.setObjectName("pinName")
        self.name_label.setFixedWidth(48)
        lay.addWidget(self.name_label)

        self.alias_label = QLabel("")
        self.alias_label.setObjectName("pinAlias")
        lay.addWidget(self.alias_label, 1)

        self.dir_btn = QPushButton("IN")
        self.dir_btn.setObjectName("pinMini")
        self.dir_btn.setFixedWidth(36)
        self.dir_btn.setToolTip("Toggle direction (Dir Set +0x04 / Dir Clr +0x10)")
        self.dir_btn.clicked.connect(lambda: on_dir(self.group, self.pin))
        lay.addWidget(self.dir_btn)

        self.level_btn = QPushButton("-")
        self.level_btn.setObjectName("pinMini")
        self.level_btn.setFixedWidth(28)
        self.level_btn.setToolTip(
            "Toggle output level (Out Set +0x00 / Out Clr +0x0C); "
            "disabled when direction is INPUT")
        self.level_btn.clicked.connect(lambda: on_level(self.group, self.pin))
        lay.addWidget(self.level_btn)

        self.pull_btn = QPushButton("Z")
        self.pull_btn.setObjectName("pinMini")
        self.pull_btn.setFixedWidth(32)
        self.pull_btn.setToolTip("Cycle pull: Hi-Z -> PU -> PD")
        self.pull_btn.clicked.connect(lambda: on_pull(self.group, self.pin))
        lay.addWidget(self.pull_btn)

        self.led = QFrame()
        self.led.setObjectName("pinLed")
        lay.addWidget(self.led)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._on_select(self.group, self.pin, event.modifiers())
        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        self._on_menu(self.group, self.pin, event.globalPos())
