from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QPushButton, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QCursor

from ui.theme import Colors, Radius


class _SubMenuItem(QPushButton):

    def __init__(self, text, key, position="middle", parent=None):
        super().__init__(text, parent)
        self.key = key
        self.position = position
        self.selected = False
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setMinimumHeight(44)
        self._apply_style()

    def set_selected(self, selected: bool):
        self.selected = selected
        self._apply_style()

    def _apply_style(self):
        radius_top = f"{Radius.card}px" if self.position == "top" else "0px"
        radius_bottom = f"{Radius.card}px" if self.position == "bottom" else "0px"

        if self.selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    border: none;
                    background-color: {Colors.submenu_item_selected_bg};
                    color: {Colors.submenu_item_selected_text};
                    text-align: left;
                    padding: 0 18px;
                    font-size: 14px;
                    border-top-left-radius: {radius_top};
                    border-top-right-radius: {radius_top};
                    border-bottom-left-radius: {radius_bottom};
                    border-bottom-right-radius: {radius_bottom};
                }}
                QPushButton:hover {{
                    background-color: {Colors.submenu_item_selected_hover};
                    color: #ffffff;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    border: none;
                    background-color: transparent;
                    color: {Colors.submenu_item_text};
                    text-align: left;
                    padding: 0 18px;
                    font-size: 14px;
                    border-top-left-radius: {radius_top};
                    border-top-right-radius: {radius_top};
                    border-bottom-left-radius: {radius_bottom};
                    border-bottom-right-radius: {radius_bottom};
                }}
                QPushButton:hover {{
                    background-color: {Colors.submenu_item_hover_bg};
                    color: #ffffff;
                }}
            """)


class SidebarSubMenu(QWidget):

    item_clicked = Signal(str)

    def __init__(self, menu_items: list, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)

        self._hovered = False
        self.current_key = None
        self.buttons: dict[str, _SubMenuItem] = {}

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(10, 10, 10, 10)
        self.outer_layout.setSpacing(0)

        self.panel = QFrame(self)
        self.panel.setObjectName("sidebarSubMenuPanel")
        self.panel.setStyleSheet(f"""
            QFrame#sidebarSubMenuPanel {{
                background-color: {Colors.submenu_bg};
                border: none;
                border-radius: {Radius.card}px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 110))
        self.panel.setGraphicsEffect(shadow)

        self.outer_layout.addWidget(self.panel)

        self._inner_layout = QVBoxLayout(self.panel)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(0)

        total = len(menu_items)
        for i, (key, text) in enumerate(menu_items):
            if i == 0:
                position = "top"
            elif i == total - 1:
                position = "bottom"
            else:
                position = "middle"

            btn = _SubMenuItem(text, key, position=position, parent=self.panel)
            btn.clicked.connect(lambda checked=False, k=key: self.item_clicked.emit(k))
            self._inner_layout.addWidget(btn)
            self.buttons[key] = btn

        self.hide()

    def set_current_item(self, key: str):
        self.current_key = key
        for item_key, btn in self.buttons.items():
            btn.set_selected(item_key == key)

    def enterEvent(self, event):
        self._hovered = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        super().leaveEvent(event)

    def is_hovered(self):
        return self._hovered
