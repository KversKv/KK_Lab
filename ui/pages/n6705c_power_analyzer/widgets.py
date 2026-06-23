#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from ui.resource_path import get_resource_base
from PySide6.QtWidgets import QWidget, QHBoxLayout
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, Property, QRectF, QEasingCurve
from PySide6.QtGui import QFont, QPainter, QColor, QPen


CHANNEL_COLORS = {
    1: {"accent": "#d4a514", "bg": "#1a1708", "border": "#3d2e08"},
    2: {"accent": "#18b67a", "bg": "#081a14", "border": "#0a3d28"},
    3: {"accent": "#2f6fed", "bg": "#081028", "border": "#0c2a5e"},
    4: {"accent": "#d14b72", "bg": "#1a080e", "border": "#3d0c22"},
}

CHANNEL_THEMES = {
    1: {
        "accent": "#d4a514", "accent_hover": "#e3b729",
        "accent_soft": "#342808", "accent_border": "#7a5e12", "text_dim": "#c9b06a"
    },
    2: {
        "accent": "#18b67a", "accent_hover": "#21c487",
        "accent_soft": "#0a2a20", "accent_border": "#14694b", "text_dim": "#7bc7a8"
    },
    3: {
        "accent": "#2f6fed", "accent_hover": "#4680f0",
        "accent_soft": "#0c2048", "accent_border": "#264d9b", "text_dim": "#8db4ff"
    },
    4: {
        "accent": "#d14b72", "accent_hover": "#df5f85",
        "accent_soft": "#34111d", "accent_border": "#7e2f47", "text_dim": "#d79ab1"
    }
}

CONTENT_BG = "#0b1020"
TAB_BAR_BG = "#07111f"
INACTIVE_TAB_BG = "#0b1222"
INACTIVE_TAB_HOVER_BG = "#0f1a30"

ROOT_BG = "#07111f"
PANEL_BG = "#0a1930"
PANEL_BORDER = "#132849"
CARD_BG = "#0b1b34"
CARD_BORDER = "#102746"
INPUT_BG = "#091426"
INPUT_BORDER = "#17345f"
DISABLED_BG = "#070f1e"
DISABLED_BORDER = "#0d1a30"
DISABLED_TEXT = "#4a5a7a"
DISABLED_BTN_BG = "#0D1734"
DISABLED_BTN_BORDER = "#18264A"
MUTED_TEXT = "#8ea6cf"
LABEL_DIM = "#7890bb"
PREFIX_TEXT = "#6a8ab8"
UNIT_TEXT = "#6a84b0"
VALUE_OFF_COLOR = "#4a5a7a"
MODE_INACTIVE_TEXT = "#8a9abb"
CONTAINER_RADIUS = "12px"
WIDGET_RADIUS = "8px"


class SlideToggle(QWidget):
    clicked = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._knob_x = 3.0
        self._accent_color = QColor("#d4a514")
        self._off_bg = QColor("#25314a")
        self._off_border = QColor("#3a4f75")
        self._knob_color = QColor("#ffffff")
        self.setFixedSize(64, 28)
        self.setCursor(Qt.PointingHandCursor)

        self._animation = QPropertyAnimation(self, b"knob_x", self)
        self._animation.setDuration(180)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_knob_x(self):
        return self._knob_x

    def _set_knob_x(self, val):
        self._knob_x = val
        self.update()

    knob_x = Property(float, _get_knob_x, _set_knob_x)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked == checked:
            return
        self._checked = checked
        end = self.width() - self.height() + 3.0 if checked else 3.0
        self._animation.stop()
        self._animation.setStartValue(self._knob_x)
        self._animation.setEndValue(end)
        self._animation.start()

    def setAccentColor(self, color_str):
        self._accent_color = QColor(color_str)
        self.update()

    def mousePressEvent(self, event):
        if not self.isEnabled():
            return
        if event.button() == Qt.LeftButton:
            self.setChecked(not self._checked)
            self.clicked.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2.0
        knob_d = h - 6.0

        disabled = not self.isEnabled()

        if disabled:
            bg = QColor("#0d1525")
            border = QColor("#162038")
            knob_color = QColor("#2a3a5a")
        elif self._checked:
            bg = self._accent_color
            border = self._accent_color.lighter(120)
            knob_color = self._knob_color
        else:
            bg = self._off_bg
            border = self._off_border
            knob_color = self._knob_color

        p.setPen(QPen(border, 1.0))
        p.setBrush(bg)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)

        font = p.font()
        font.setPixelSize(10)
        font.setWeight(QFont.Bold)
        p.setFont(font)

        if disabled:
            p.setPen(QColor("#2a3a5a"))
            p.drawText(QRectF(knob_d + 6, 0, w - knob_d - 16, h), Qt.AlignVCenter | Qt.AlignRight, "OFF")
        elif self._checked:
            p.setPen(QColor("#111111"))
            p.drawText(QRectF(8, 0, w - knob_d - 10, h), Qt.AlignVCenter | Qt.AlignLeft, "ON")
        else:
            p.setPen(QColor("#8ea6cf"))
            p.drawText(QRectF(knob_d + 6, 0, w - knob_d - 16, h), Qt.AlignVCenter | Qt.AlignRight, "OFF")

        p.setPen(Qt.NoPen)
        p.setBrush(knob_color)
        p.drawEllipse(QRectF(self._knob_x, 3.0, knob_d, knob_d))

        p.end()


class ChannelTabBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._border_color = "#14305e"
        self._active_tab_rect = None
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {TAB_BAR_BG};")

        self._inner_layout = QHBoxLayout(self)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(0)

    def set_border_color(self, color):
        self._border_color = color
        self.update()

    def set_active_tab_rect(self, rect):
        self._active_tab_rect = rect
        self.update()

    def layout(self):
        return self._inner_layout

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, False)
        pen = QPen(QColor(self._border_color), 1)
        p.setPen(pen)

        y = self.height() - 1

        if self._active_tab_rect:
            r = self._active_tab_rect
            if r.left() > 0:
                p.drawLine(0, y, r.left(), y)
            if r.right() < self.width():
                p.drawLine(r.right(), y, self.width(), y)
        else:
            p.drawLine(0, y, self.width(), y)

        p.end()


_ICONS_DIR = os.path.join(
    get_resource_base(),
    "resources", "icons"
)

_PAGE_SVGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "pages", "n6705c_power_analyzer_SVGs"
)

_ZAP_ICON_PATH = os.path.join(_PAGE_SVGS_DIR, "zap.svg")


def _get_checkmark_path(accent_color):
    safe_name = accent_color.replace("#", "").replace(" ", "")
    icons_dir = _ICONS_DIR
    return {
        "checked": os.path.join(icons_dir, f"checked_{safe_name}.svg").replace("\\", "/"),
        "unchecked": os.path.join(icons_dir, f"unchecked_{safe_name}.svg").replace("\\", "/"),
    }


def _format_current(current_A):
    abs_i = abs(current_A)
    if abs_i >= 1:
        return f"{current_A:.3f} A"
    elif abs_i >= 1e-3:
        return f"{current_A*1e3:.3f} mA"
    elif abs_i >= 1e-6:
        return f"{current_A*1e6:.3f} \u00b5A"
    elif abs_i >= 1e-9:
        return f"{current_A*1e9:.3f} nA"
    else:
        return f"{current_A:.3e} A"


def _batch_channel_button_style():
    return f"""
        QPushButton {{
            background-color: #111d36; color: #7a8fb5;
            border: 1px solid #1e3050; border-radius: {WIDGET_RADIUS};
            padding: 7px 0px; font-size: 12px; font-weight: 600;
        }}
        QPushButton:checked {{ background-color: #1a2a50; color: #c0d0f0; border: 1px solid #3a5a90; }}
        QPushButton:hover {{ background-color: #182844; }}
        QPushButton:disabled {{ background-color: #0b1730; color: {DISABLED_TEXT}; border: 1px solid {DISABLED_BTN_BORDER}; }}
    """


def collapsible_header_style(collapsed):
    if collapsed:
        return f"""
            QPushButton {{
                background-color: {PANEL_BG}; color: {MUTED_TEXT};
                border: 1px solid {PANEL_BORDER}; border-radius: {WIDGET_RADIUS};
                padding: 8px 16px; font-size: 12px; font-weight: 700; text-align: left;
            }}
            QPushButton:hover {{ background-color: #0e1f3d; color: #b8d0f0; }}
        """
    else:
        return f"""
            QPushButton {{
                background-color: {PANEL_BG}; color: #b8d0f0;
                border: 1px solid {PANEL_BORDER}; border-bottom: none;
                border-top-left-radius: {WIDGET_RADIUS}; border-top-right-radius: {WIDGET_RADIUS};
                border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
                padding: 8px 16px; font-size: 12px; font-weight: 700; text-align: left;
            }}
            QPushButton:hover {{ background-color: #0e1f3d; color: #d0e4ff; }}
        """
