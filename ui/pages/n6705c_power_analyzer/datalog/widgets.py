#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pyqtgraph as pg
from PySide6.QtCore import (
    QByteArray,
    QRect,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QStyle,
    QStyleOptionTab,
    QStylePainter,
    QTabBar,
    QVBoxLayout,
    QWidget,
)
from resource_path import get_resource_base
from ui.widgets.dark_combobox import DarkComboBox
from ui.pages.n6705c_power_analyzer.datalog.helpers import _auto_format, _parse_value_with_unit

class PairAnnotationItem(pg.TextItem):
    """成对 Marker 区间注释文本框：左键按住拖拽自由移动，右键弹出字体大小菜单。

    注意：不能用 ItemIsMovable 实现拖拽——它会让 Qt 层连右键按下也一并 accept 成为
    grabber，吞掉 scene 的点击分发；这里沿用 InfiniteLine 的 pyqtgraph 原生
    hoverEvent/mouseDragEvent/mouseClickEvent 分发模式。
    """

    def __init__(self, html, moved_callback, context_callback, **kwargs):
        super().__init__(html=html, **kwargs)
        self._moved_callback = moved_callback
        self._context_callback = context_callback
        self._drag_offset = None
        self.pair_ref = None      # ("AB", None) 或 ("X", pair_idx)，由创建方赋值
        self.default_pos = None   # 未加手动偏移时的默认锚点 (x, y)，由创建方赋值
        self.setCursor(Qt.SizeAllCursor)

    def hoverEvent(self, ev):
        if not ev.isExit():
            ev.acceptDrags(Qt.LeftButton)

    def mouseDragEvent(self, ev):
        if ev.button() != Qt.LeftButton:
            return
        ev.accept()
        if ev.isStart():
            self._drag_offset = self.pos() - self.mapToParent(ev.buttonDownPos())
        if self._drag_offset is not None:
            self.setPos(self._drag_offset + self.mapToParent(ev.pos()))
        if ev.isFinish():
            self._drag_offset = None
            if self._moved_callback is not None:
                self._moved_callback(self)

    def mouseClickEvent(self, ev):
        if ev.button() == Qt.RightButton and self._context_callback is not None:
            ev.accept()
            self._context_callback(self, ev.screenPos())


class ToggleLabel(QLabel):
    toggled = Signal(bool)

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._checked = False
        self.setAlignment(Qt.AlignCenter)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(24)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        self._checked = checked
        self.toggled.emit(checked)

    def mousePressEvent(self, event):
        if not self.isEnabled():
            return
        self._checked = not self._checked
        self.toggled.emit(self._checked)
        super().mousePressEvent(event)

    def blockSignals(self, b):
        super().blockSignals(b)


class ScaleOffsetEdit(QLineEdit):
    wheel_adjusted = Signal()

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setFocusPolicy(Qt.StrongFocus)
        # 纵向随行高拉伸：行高由 ToggleLabel(24) 决定，QLineEdit 默认 Fixed 会短一截，
        # 导致相邻行输入框间距 (2+高度差) 与 V/I/P 按钮间距 (2) 不一致
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.accept()
            return
        factor = 1.1 if delta > 0 else 0.9
        current = _parse_value_with_unit(self.text())
        if current is None:
            event.accept()
            return
        new_val = current * factor
        base_unit = self.property("base_unit") or "mA"
        self.setText(_auto_format(new_val, base_unit))
        self.wheel_adjusted.emit()
        event.accept()


class ChannelNameLabel(QWidget):
    renamed = Signal(str, str)

    def __init__(self, key, display_name, color, parent=None):
        super().__init__(parent)
        self._key = key
        self._display_name = display_name
        self._color = color

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 0, 2, 0)
        layout.setSpacing(0)

        self._label = QLabel(display_name)
        self._label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self._label.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: 800; border: none; padding: 0 2px;"
        )
        layout.addWidget(self._label)

        self._edit = QLineEdit(display_name)
        self._edit.setAlignment(Qt.AlignRight)
        self._edit.setStyleSheet(
            f"background: #0c1a35; color: {color}; font-size: 13px; font-weight: 800; "
            f"border: 1px solid {color}; border-radius: 1px; padding: 0 2px;"
        )
        self._edit.hide()
        layout.addWidget(self._edit)

        self._edit.returnPressed.connect(self._finish_edit)
        self._edit.editingFinished.connect(self._finish_edit)

    def mouseDoubleClickEvent(self, event):
        self._label.hide()
        self._edit.setText(self._display_name)
        self._edit.show()
        self._edit.setFocus()
        self._edit.selectAll()

    def _finish_edit(self):
        new_name = self._edit.text().strip()
        if new_name and new_name != self._display_name:
            self._display_name = new_name
            self._label.setText(new_name)
            self.renamed.emit(self._key, new_name)
        self._edit.hide()
        self._label.show()

    @property
    def key(self):
        return self._key


class ChannelConfigTabBar(QTabBar):
    NORMAL_MIN_WIDTH = 60
    IMPORT_TAB_WIDTH = 34
    IMPORT_ICON_SIZE = 16
    IMPORT_TAB_KIND = "import_plus"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_index = -1
        self.setMouseTracking(True)

    def tabSizeHint(self, index):
        size = super().tabSizeHint(index)
        if self.tabData(index) == self.IMPORT_TAB_KIND:
            return QSize(self.IMPORT_TAB_WIDTH, size.height())
        if size.width() < self.NORMAL_MIN_WIDTH:
            size.setWidth(self.NORMAL_MIN_WIDTH)
        return size

    def mouseMoveEvent(self, event):
        idx = self.tabAt(event.position().toPoint())
        if idx != self._hover_index:
            self._hover_index = idx
            self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hover_index != -1:
            self._hover_index = -1
            self.update()
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionTab()
        for index in range(self.count()):
            self.initStyleOption(option, index)
            if self.tabData(index) != self.IMPORT_TAB_KIND:
                painter.drawControl(QStyle.CE_TabBarTab, option)
                continue

            tab_rect = option.rect
            top = min(self.tabRect(i).top() for i in range(self.count()))
            full_rect = QRect(tab_rect.left(), top, tab_rect.width(), tab_rect.bottom() - top + 1)

            if index == self._hover_index:
                painter.save()
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor("#16294d")))
                hover_rect = full_rect.adjusted(2, 4, -3, -4)
                painter.drawRoundedRect(hover_rect, 6, 6)
                painter.restore()

            icon_rect = QRect(0, 0, self.IMPORT_ICON_SIZE, self.IMPORT_ICON_SIZE)
            icon_rect.moveCenter(full_rect.center())
            mode = QIcon.Selected if option.state & QStyle.State_Selected else QIcon.Normal
            self.tabIcon(index).paint(painter, icon_rect, Qt.AlignCenter, mode)


class CardFrame(QFrame):
    header_clicked = Signal()

    def __init__(self, title="", icon="", parent=None, svg_icon=None, svg_color="#8eb0e3", svg_size=14):
        super().__init__(parent)
        self.setObjectName("cardFrame")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(14, 14, 14, 14)
        self.main_layout.setSpacing(10)
        self.header_widget = None

        if title:
            if svg_icon:
                self.header_widget = QWidget()
                self.header_widget.setStyleSheet("background: transparent; border: none;")
                title_row = QHBoxLayout(self.header_widget)
                title_row.setSpacing(6)
                title_row.setContentsMargins(0, 0, 0, 0)
                svg_path = os.path.join(get_resource_base(), "resources", "pages", "n6705c_power_analyzer_SVGs", svg_icon)
                with open(svg_path, "r", encoding="utf-8") as f:
                    svg_data = f.read().replace("currentColor", svg_color)
                renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
                pixmap = QPixmap(svg_size, svg_size)
                pixmap.fill(QColor(0, 0, 0, 0))
                painter = QPainter(pixmap)
                renderer.render(painter)
                painter.end()
                icon_lbl = QLabel()
                icon_lbl.setPixmap(pixmap)
                icon_lbl.setFixedSize(svg_size, svg_size)
                icon_lbl.setStyleSheet("border: none; background: transparent;")
                title_row.addWidget(icon_lbl)
                self.title_label = QLabel(title)
                self.title_label.setObjectName("cardTitle")
                title_row.addWidget(self.title_label)
                title_row.addStretch()
                self.main_layout.addWidget(self.header_widget)
            else:
                self.title_label = QLabel(f"{icon}  {title}" if icon else title)
                self.title_label.setObjectName("cardTitle")
                self.main_layout.addWidget(self.title_label)

    def set_header_clickable(self, tooltip=""):
        if self.header_widget is None:
            return
        self.header_widget.setCursor(Qt.PointingHandCursor)
        if tooltip:
            self.header_widget.setToolTip(tooltip)
        self.header_widget.mousePressEvent = self._on_header_mouse_press
        self.header_widget.enterEvent = self._on_header_enter
        self.header_widget.leaveEvent = self._on_header_leave

    def _on_header_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.header_clicked.emit()
            event.accept()

    def _on_header_enter(self, event):
        self.title_label.setStyleSheet("color: #8eb0e3;")
        event.accept()

    def _on_header_leave(self, event):
        self.title_label.setStyleSheet("")
        event.accept()


class ClickableHeader(QWidget):
    clicked = Signal()

    def __init__(self, title="", svg_icon=None, svg_color="#8eb0e3", svg_size=14, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("background: transparent; border: none;")
        row = QHBoxLayout(self)
        row.setSpacing(6)
        row.setContentsMargins(0, 0, 0, 0)

        if svg_icon:
            svg_path = os.path.join(get_resource_base(), "resources", "pages", "n6705c_power_analyzer_SVGs", svg_icon)
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_data = f.read().replace("currentColor", svg_color)
            renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
            pixmap = QPixmap(svg_size, svg_size)
            pixmap.fill(QColor(0, 0, 0, 0))
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            icon_lbl = QLabel()
            icon_lbl.setPixmap(pixmap)
            icon_lbl.setFixedSize(svg_size, svg_size)
            icon_lbl.setStyleSheet("border: none; background: transparent;")
            row.addWidget(icon_lbl)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")
        row.addWidget(self.title_label)
        row.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()

    def enterEvent(self, event):
        self.title_label.setStyleSheet("color: #8eb0e3;")

    def leaveEvent(self, event):
        self.title_label.setStyleSheet("")


class FixedPopupComboBox(DarkComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def showPopup(self):
        super().showPopup()
        view = self.view()
        if view and view.window():
            popup = view.window()
            global_pos = self.mapToGlobal(self.rect().bottomLeft())
            popup.move(global_pos.x(), global_pos.y())
