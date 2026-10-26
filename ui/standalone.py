import os
import sys

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from log_config import get_logger
from resource_path import get_resource_base

logger = get_logger(__name__)

DEFAULT_STANDALONE_WINDOW_SIZE = (1600, 900)


def _ensure_streams():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")


def _qt_message_handler(msg_type, context, message):
    if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
        return
    logger.debug("%s:%s - %s", context.file, context.line, message)


def resize_and_center_window(window, size=DEFAULT_STANDALONE_WINDOW_SIZE):
    width, height = size
    app = QApplication.instance()
    screen = window.screen() or (app.primaryScreen() if app is not None else None)
    if screen is None:
        window.resize(width, height)
        return

    available = screen.availableGeometry()
    x = available.x() + (available.width() - width) // 2
    y = available.y() + (available.height() - height) // 2
    window.setGeometry(x, y, width, height)


def apply_window_icon(window, icon_name):
    icon_path = os.path.join(
        get_resource_base(), "resources", "icons", f"{icon_name}.ico"
    )
    if not os.path.isfile(icon_path):
        logger.warning("Window icon not found: %s", icon_path)
        return

    icon = QIcon(icon_path)
    window.setWindowIcon(icon)
    app = QApplication.instance()
    if app is not None:
        app.setWindowIcon(icon)


def run_standalone_widget(
    widget_factory, title, size=DEFAULT_STANDALONE_WINDOW_SIZE, icon_name=None
):
    _ensure_streams()
    qInstallMessageHandler(_qt_message_handler)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    window = widget_factory()
    window.setWindowTitle(title)
    if icon_name is not None:
        apply_window_icon(window, icon_name)
    resize_and_center_window(window, size)
    window.show()

    return app.exec()
