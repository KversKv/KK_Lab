from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QFrame, QPushButton, QGraphicsDropShadowEffect,
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint
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

        self._show_anim_opacity = None
        self._show_anim_pos = None
        self._hide_anim_opacity = None
        self._target_pos = QPoint()
        self._animating_hide = False

        super().hide()

    def show(self):
        if self.isVisible() and not self._animating_hide:
            return
        self._animating_hide = False
        self._stop_animations()
        self.setWindowOpacity(0.0)
        super().show()
        self._animate_show()

    def hide(self):
        if self.isVisible() and not self._animating_hide:
            self._animate_hide()
        elif not self._animating_hide:
            super().hide()

    def force_hide(self):
        self._animating_hide = False
        self._stop_animations()
        self.setWindowOpacity(1.0)
        super().hide()

    def _animate_show(self):
        self._stop_animations()
        self.setWindowOpacity(0.0)

        self._show_anim_opacity = QPropertyAnimation(self, b"windowOpacity", self)
        self._show_anim_opacity.setDuration(100)
        self._show_anim_opacity.setStartValue(0.0)
        self._show_anim_opacity.setEndValue(1.0)
        self._show_anim_opacity.setEasingCurve(QEasingCurve.OutCubic)

        self._target_pos = self.pos()
        start_pos = QPoint(self._target_pos.x(), self._target_pos.y() + 4)
        self.move(start_pos)

        self._show_anim_pos = QPropertyAnimation(self, b"pos", self)
        self._show_anim_pos.setDuration(100)
        self._show_anim_pos.setStartValue(start_pos)
        self._show_anim_pos.setEndValue(self._target_pos)
        self._show_anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        self._show_anim_opacity.start(QPropertyAnimation.DeleteWhenStopped)
        self._show_anim_pos.start(QPropertyAnimation.DeleteWhenStopped)

    def _animate_hide(self):
        self._animating_hide = True
        self._stop_animations()

        self._hide_anim_opacity = QPropertyAnimation(self, b"windowOpacity", self)
        self._hide_anim_opacity.setDuration(80)
        self._hide_anim_opacity.setStartValue(self.windowOpacity())
        self._hide_anim_opacity.setEndValue(0.0)
        self._hide_anim_opacity.setEasingCurve(QEasingCurve.InCubic)
        self._hide_anim_opacity.finished.connect(self._on_hide_finished)
        self._hide_anim_opacity.start(QPropertyAnimation.DeleteWhenStopped)

    def _on_hide_finished(self):
        self._animating_hide = False
        self.setWindowOpacity(1.0)
        super(SidebarSubMenu, self).hide()

    def _stop_animations(self):
        for anim in (self._show_anim_opacity, self._show_anim_pos, self._hide_anim_opacity):
            if anim is None:
                continue
            try:
                if anim.state() == QPropertyAnimation.Running:
                    anim.stop()
            except RuntimeError:
                pass
        self._show_anim_opacity = None
        self._show_anim_pos = None
        self._hide_anim_opacity = None

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
