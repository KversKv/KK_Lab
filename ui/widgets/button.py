import os
from ui.resource_path import get_resource_base
from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QIcon, QPainter, QPixmap, QTransform
from PySide6.QtCore import QSize, QTimer, Qt, QRectF
from PySide6.QtSvg import QSvgRenderer

_ICONS_DIR = os.path.join(
    get_resource_base(),
    "resources", "icons"
)

_SEARCH_ICON_PATH = os.path.join(_ICONS_DIR, "search.svg")
_LINK_ICON_PATH = os.path.join(_ICONS_DIR, "link.svg")
_UNLINK_ICON_PATH = os.path.join(_ICONS_DIR, "unlink.svg")


def search_button_style():
    return """
        QPushButton {
            background-color: #13254b;
            border: 1px solid #22376A;
            border-radius: 8px;
            color: #dce7ff;
            font-weight: 600;
            padding: 2px 8px;
        }
        QPushButton:hover {
            background-color: #1C2D55;
            border: 1px solid #3A5A9F;
        }
        QPushButton:pressed {
            background-color: #102040;
        }
        QPushButton:disabled {
            background-color: #0b1430;
            color: #5c7096;
            border: 1px solid #1a2850;
        }
    """


def connect_button_style():
    return """
        QPushButton {
            background-color: #053b38;
            border: 1px solid #08c9a5;
            border-radius: 8px;
            color: #10e7bc;
            font-weight: 700;
            padding: 2px 8px;
        }
        QPushButton:hover {
            background-color: #064744;
            border: 1px solid #19f0c5;
            color: #43f3d0;
        }
        QPushButton:pressed {
            background-color: #042f2d;
        }
        QPushButton:disabled {
            background-color: #0D1734;
            color: #3a4a6a;
            border: 1px solid #18264A;
        }
    """


def disconnect_button_style():
    return """
        QPushButton {
            background-color: #3a0828;
            border: 1px solid #d61b67;
            border-radius: 8px;
            color: #ffb7d3;
            font-weight: 700;
            padding: 2px 8px;
        }
        QPushButton:hover {
            background-color: #4a0b31;
            border: 1px solid #f0287b;
            color: #ffd0e2;
        }
        QPushButton:pressed {
            background-color: #330722;
        }
        QPushButton:disabled {
            background-color: #0D1734;
            color: #3a4a6a;
            border: 1px solid #18264A;
        }
    """


class SpinningSearchButton(QPushButton):
    def __init__(self, parent=None, icon_size: int = 16):
        super().__init__(parent)
        self._icon_size = icon_size
        self._angle = 0.0
        self._spinning = False
        self._svg_renderer = None

        if os.path.isfile(_SEARCH_ICON_PATH):
            self._svg_renderer = QSvgRenderer(_SEARCH_ICON_PATH)

        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._on_tick)

        self.setText("")
        self.setStyleSheet(search_button_style())

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
        if not self._svg_renderer:
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
        painter.translate(-s / 2.0, -s / 2.0)

        self._svg_renderer.render(painter, QRectF(0, 0, s, s))
        painter.end()


def apply_search_button(btn: QPushButton, icon_size: int = 16):
    btn.setText("")
    btn.setStyleSheet(search_button_style())
    if os.path.isfile(_SEARCH_ICON_PATH):
        btn.setIcon(QIcon(_SEARCH_ICON_PATH))
        btn.setIconSize(QSize(icon_size, icon_size))


def update_connect_button_state(btn: QPushButton, connected: bool):
    if connected:
        btn.setText("Disconnect")
        btn.setStyleSheet(disconnect_button_style())
        if os.path.isfile(_UNLINK_ICON_PATH):
            btn.setIcon(QIcon(_UNLINK_ICON_PATH))
            btn.setIconSize(QSize(16, 16))
    else:
        btn.setText("Connect")
        btn.setStyleSheet(connect_button_style())
        if os.path.isfile(_LINK_ICON_PATH):
            btn.setIcon(QIcon(_LINK_ICON_PATH))
            btn.setIconSize(QSize(16, 16))
        else:
            btn.setIcon(QIcon())
