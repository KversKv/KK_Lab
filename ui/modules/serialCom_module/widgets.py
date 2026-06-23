#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import serial
import serial.tools.list_ports

from PySide6.QtWidgets import (
    QPushButton, QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QWidget, QLabel, QComboBox, QDialogButtonBox,
    QGraphicsDropShadowEffect, QGraphicsBlurEffect,
)
from PySide6.QtCore import Qt, QRectF, QTimer, QObject, Signal
from PySide6.QtGui import QPixmap, QPainter, QIcon, QColor
from PySide6.QtSvg import QSvgRenderer

from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from ui.modules.serialCom_module.serialCom_module_frame import (
    _SERIAL_BTN_ICON_SIZE, _SERIAL_BTN_HEIGHT, _SERIAL_BTN_RADIUS,
    _SEARCH_ICON_PATH, _UNLINK_ICON_PATH, _LINK_ICON_PATH,
    _serial_search_style, _serial_disconnect_style, _serial_connect_style,
    _SVG_SERIAL_DIR, _CLR_SEND_BG, _CLR_TEXT_BTN_LOG, _DLG_STYLE,
    frameless_chrome_style, dialog_backdrop_style,
    dialog_ok_button_style, dialog_cancel_button_style,
)


class _SerialSearchButton(QPushButton):
    def __init__(self, parent=None, icon_size=_SERIAL_BTN_ICON_SIZE,
                 btn_height=_SERIAL_BTN_HEIGHT, btn_radius=_SERIAL_BTN_RADIUS):
        super().__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)
        self._icon_size = icon_size
        self._angle = 0.0
        self._spinning = False
        self._icon_pixmap = None

        if os.path.isfile(_SEARCH_ICON_PATH):
            renderer = QSvgRenderer(_SEARCH_ICON_PATH)
            pm = QPixmap(icon_size, icon_size)
            pm.fill(Qt.transparent)
            p = QPainter(pm)
            p.setRenderHint(QPainter.Antialiasing)
            p.setRenderHint(QPainter.SmoothPixmapTransform)
            renderer.render(p, QRectF(0, 0, icon_size, icon_size))
            p.end()
            self._icon_pixmap = pm

        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._on_tick)

        self.setText("")
        self.setStyleSheet(_serial_search_style(h=btn_height, r=btn_radius))

    def start_spinning(self):
        if self._spinning:
            return
        self._spinning = True
        self._angle = 0.0
        self._timer.start()
        self.update()

    def stop_spinning(self):
        if not self._spinning:
            return
        self._spinning = False
        self._timer.stop()
        self._angle = 0.0
        self.update()

    def _on_tick(self):
        self._angle = (self._angle + 10.0) % 360.0
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._icon_pixmap is None:
            return

        s = self._icon_size
        cx = self.width() / 2.0
        cy = self.height() / 2.0

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        painter.translate(cx, cy)
        if self._spinning:
            painter.rotate(self._angle)
        painter.drawPixmap(int(-s / 2.0), int(-s / 2.0), self._icon_pixmap)
        painter.end()


_SERIAL_BTN_FIXED_WIDTH = 104


def _update_serial_btn_state(btn, connected,
                             h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS,
                             icon_size=_SERIAL_BTN_ICON_SIZE):
    from PySide6.QtCore import QSize as _QSize
    btn.setFixedWidth(_SERIAL_BTN_FIXED_WIDTH)
    if connected:
        btn.setText("Disconnect")
        btn.setStyleSheet(_serial_disconnect_style(h=h, r=r))
        if os.path.isfile(_UNLINK_ICON_PATH):
            btn.setIcon(QIcon(_UNLINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
    else:
        btn.setText("Connect")
        btn.setStyleSheet(_serial_connect_style(h=h, r=r))
        if os.path.isfile(_LINK_ICON_PATH):
            btn.setIcon(QIcon(_LINK_ICON_PATH))
            btn.setIconSize(_QSize(icon_size, icon_size))
        else:
            btn.setIcon(QIcon())


class _SearchSerialPortWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        try:
            ports = serial.tools.list_ports.comports()
            result = [f"{p.device} - {p.description}" for p in ports]
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _FramelessChromeDialog(QDialog):
    """统一的无边框圆角对话框基类。

    提供：自绘标题栏（图标 + 标题 + 关闭按钮）、圆角容器、柔和投影、
    标题栏拖动、以及弹出时主窗口模糊遮罩。子类把内容控件加入
    ``self._content`` 布局，并用 ``self._apply_content_style(qss)``
    合并自身样式表。
    """

    def __init__(self, parent=None, title="", icon_name="edit.svg"):
        super().__init__(parent)
        self.setObjectName("scChromeDialog")
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self._drag_pos = None
        self._backdrop = None
        self._blur_effect = None
        self._content_qss = ""

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

        shell = QVBoxLayout(container)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        header = QFrame()
        header.setObjectName("scEditorHeader")
        header.installEventFilter(self)
        self._header = header
        header_row = QHBoxLayout(header)
        header_row.setContentsMargins(24, 16, 20, 16)
        header_row.setSpacing(10)
        title_icon = QLabel()
        _ico = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, icon_name), _CLR_SEND_BG, 18)
        if not _ico.isNull():
            title_icon.setPixmap(_ico.pixmap(18, 18))
        header_row.addWidget(title_icon)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("scEditorTitle")
        self._title_lbl = title_lbl
        header_row.addWidget(title_lbl)
        header_row.addStretch()
        close_btn = QPushButton("\u2715")
        close_btn.setObjectName("scEditorClose")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setFixedSize(28, 28)
        close_btn.setAutoDefault(False)
        close_btn.setDefault(False)
        close_btn.clicked.connect(self.reject)
        header_row.addWidget(close_btn)
        shell.addWidget(header)

        body_host = QFrame()
        body_host.setObjectName("scChromeBody")
        self._content = QVBoxLayout(body_host)
        self._content.setContentsMargins(24, 20, 24, 22)
        self._content.setSpacing(12)
        shell.addWidget(body_host, 1)

        self.setStyleSheet(self._chrome_qss())

    def set_title(self, text):
        self._title_lbl.setText(text)

    def _apply_content_style(self, qss):
        self._content_qss = qss or ""
        self.setStyleSheet(self._chrome_qss() + self._content_qss)

    def _chrome_qss(self):
        return frameless_chrome_style()

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


class _MixinSerialSettingsDialog(_FramelessChromeDialog):
    """SerialComMixin 用的轻量串口参数设置对话框
    （波特率/数据位/停止位/校验/流控）。

    与本文件内独立窗口模式下的多标签 ``_SerialSettingsDialog`` 区分开，
    后者由 ``_sc_open_settings_dialog`` 使用。
    """

    _BAUDRATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600, 1500000, 2000000]
    _BYTESIZES = [
        ("5", 5), ("6", 6), ("7", 7), ("8", 8),
    ]
    _STOPBITS = [
        ("1", serial.STOPBITS_ONE),
        ("1.5", serial.STOPBITS_ONE_POINT_FIVE),
        ("2", serial.STOPBITS_TWO),
    ]
    _PARITIES = [
        ("None", serial.PARITY_NONE),
        ("Even", serial.PARITY_EVEN),
        ("Odd", serial.PARITY_ODD),
        ("Mark", serial.PARITY_MARK),
        ("Space", serial.PARITY_SPACE),
    ]
    _FLOWS = [
        ("None", (False, False)),
        ("XON/XOFF (Software)", (True, False)),
        ("RTS/CTS (Hardware)", (False, True)),
    ]

    def __init__(self, parent=None, *,
                 baudrate=921600,
                 bytesize=8,
                 stopbits=serial.STOPBITS_ONE,
                 parity=serial.PARITY_NONE,
                 xonxoff=False,
                 rtscts=False,
                 connected=False):
        super().__init__(parent, title="SERIAL PORT SETTINGS", icon_name="settings.svg")
        try:
            self._apply_content_style(_DLG_STYLE)
        except Exception:
            pass

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setContentsMargins(0, 0, 0, 4)

        def _label(text):
            lab = QLabel(text)
            lab.setStyleSheet(f"color:{_CLR_TEXT_BTN_LOG};font-size:12px;background:transparent;border:none;")
            return lab

        self._baud_combo = QComboBox()
        self._baud_combo.setEditable(True)
        for br in self._BAUDRATES:
            self._baud_combo.addItem(str(br), br)
        self._baud_combo.setCurrentText(str(baudrate))

        self._bytesize_combo = QComboBox()
        for label, val in self._BYTESIZES:
            self._bytesize_combo.addItem(label, val)
        self._select_by_data(self._bytesize_combo, bytesize)

        self._stopbits_combo = QComboBox()
        for label, val in self._STOPBITS:
            self._stopbits_combo.addItem(label, val)
        self._select_by_data(self._stopbits_combo, stopbits)

        self._parity_combo = QComboBox()
        for label, val in self._PARITIES:
            self._parity_combo.addItem(label, val)
        self._select_by_data(self._parity_combo, parity)

        self._flow_combo = QComboBox()
        for label, val in self._FLOWS:
            self._flow_combo.addItem(label, val)
        self._select_by_data(self._flow_combo, (bool(xonxoff), bool(rtscts)))

        for combo in (self._baud_combo, self._bytesize_combo, self._stopbits_combo,
                      self._parity_combo, self._flow_combo):
            combo.setMinimumWidth(180)

        form.addWidget(_label("Baudrate"),    0, 0)
        form.addWidget(self._baud_combo,      0, 1)
        form.addWidget(_label("Data Bits"),   1, 0)
        form.addWidget(self._bytesize_combo,  1, 1)
        form.addWidget(_label("Stop Bits"),   2, 0)
        form.addWidget(self._stopbits_combo,  2, 1)
        form.addWidget(_label("Parity"),      3, 0)
        form.addWidget(self._parity_combo,    3, 1)
        form.addWidget(_label("Flow Control"),4, 0)
        form.addWidget(self._flow_combo,      4, 1)

        if connected:
            warn = QLabel("Already connected. Changes apply to the next connection "
                          "(baudrate hot-applied).")
            warn.setWordWrap(True)
            warn.setStyleSheet("color:#f2994a;font-size:11px;background:transparent;border:none;")
            form.addWidget(warn, 5, 0, 1, 2)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = btn_box.button(QDialogButtonBox.Ok)
        cancel_btn = btn_box.button(QDialogButtonBox.Cancel)
        try:
            ok_btn.setStyleSheet(dialog_ok_button_style())
            cancel_btn.setStyleSheet(dialog_cancel_button_style())
        except Exception:
            pass
        ok_btn.setDefault(True)
        ok_btn.setAutoDefault(True)
        cancel_btn.setDefault(False)
        cancel_btn.setAutoDefault(False)
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)

        root = self._content
        root.setSpacing(12)
        root.addLayout(form)
        root.addWidget(btn_box)

        self.setFixedWidth(488)

    @staticmethod
    def _select_by_data(combo, data):
        for i in range(combo.count()):
            if combo.itemData(i) == data:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)

    def result_config(self) -> dict:
        try:
            baudrate = int(self._baud_combo.currentText().strip())
            if baudrate <= 0:
                raise ValueError
        except (TypeError, ValueError):
            baudrate = self._baud_combo.itemData(self._baud_combo.currentIndex()) or 921600
        flow_val = self._flow_combo.currentData() or (False, False)
        return {
            "baudrate": baudrate,
            "bytesize": self._bytesize_combo.currentData(),
            "stopbits": self._stopbits_combo.currentData(),
            "parity": self._parity_combo.currentData(),
            "xonxoff": bool(flow_val[0]),
            "rtscts": bool(flow_val[1]),
        }
