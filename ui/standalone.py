import os
import sys

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from log_config import get_logger

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


def run_standalone_widget(widget_factory, title, size=DEFAULT_STANDALONE_WINDOW_SIZE):
    _ensure_streams()
    qInstallMessageHandler(_qt_message_handler)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    window = widget_factory()
    window.setWindowTitle(title)
    resize_and_center_window(window, size)
    window.show()

    return app.exec()
