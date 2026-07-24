# -*- coding: utf-8 -*-
"""右键菜单: 使能切换 + 模式选择。"""

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout

from ui.pages.pmu.pmu_1811.constants import (
    COL_CARD_BG, COL_BORDER, COL_TEXT_MUTED, COL_TEXT, COL_BORDER_HOVER, COL_EMERALD,
)
from ui.pages.pmu.pmu_1811.models import PmuModule


class ContextMenu(QFrame):
    enable_toggled = Signal(str)
    mode_changed = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self._mod: PmuModule | None = None
        self.setStyleSheet(
            f"QFrame {{ background:{COL_CARD_BG}; border:1px solid {COL_BORDER};"
            f" border-radius:8px; }}"
            f"QLabel#menuHeader {{ color:{COL_TEXT_MUTED}; font-size:11px;"
            f" padding:6px 12px; }}"
            f"QPushButton#menuBtn {{ background:transparent; color:{COL_TEXT};"
            f" border:none; padding:8px 12px; text-align:left; font-size:12px; }}"
            f"QPushButton#menuBtn:hover {{ background:{COL_BORDER}; }}"
            f"QPushButton#menuBtn:checked {{ color:{COL_EMERALD}; font-weight:700; }}"
        )
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.header = QLabel("—", self)
        self.header.setObjectName("menuHeader")
        self._layout.addWidget(self.header)
        self.toggle_btn = QPushButton("Enable Output", self)
        self.toggle_btn.setObjectName("menuBtn")
        self.toggle_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_btn.clicked.connect(self._on_toggle)
        self._layout.addWidget(self.toggle_btn)
        self._sep = QFrame(self)
        self._sep.setFixedHeight(1)
        self._sep.setStyleSheet(f"background:{COL_BORDER}; border:none;")
        self._layout.addWidget(self._sep)
        self._mode_btns = []

    def popup(self, mod: PmuModule, pos: QPoint):
        self._mod = mod
        self.header.setText(mod.name)
        # SW: 闭合/开路; LDO/BUCK: Enable/Disable Output
        if mod.type == "SW":
            self.toggle_btn.setText("开路 (强制断开)" if mod.enabled else "闭合 (强制导通)")
        else:
            self.toggle_btn.setText("Disable Output" if mod.enabled else "Enable Output")
        for b in self._mode_btns:
            self._layout.removeWidget(b)
            b.deleteLater()
        self._mode_btns.clear()
        for m in mod.modes:
            b = QPushButton(m, self)
            b.setObjectName("menuBtn")
            b.setCheckable(True)
            b.setChecked(m == mod.mode)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, mm=m: self._on_mode(mm))
            self._layout.addWidget(b)
            self._mode_btns.append(b)
        # 无模式 (SW) 时隐藏分隔线
        self._sep.setVisible(bool(mod.modes))
        self.adjustSize()
        self.move(pos)
        self.show()

    def _on_toggle(self):
        if self._mod is not None:
            self.enable_toggled.emit(self._mod.id)
        self.close()

    def _on_mode(self, mode: str):
        if self._mod is not None:
            self.mode_changed.emit(self._mod.id, mode)
        self.close()
