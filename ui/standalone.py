import os
import sys

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

from log_config import get_logger

logger = get_logger(__name__)


def _ensure_streams():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")


def _qt_message_handler(msg_type, context, message):
    if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
        return
    logger.debug("%s:%s - %s", context.file, context.line, message)


def run_standalone_widget(widget_factory, title, size=(1200, 800)):
    _ensure_streams()
    qInstallMessageHandler(_qt_message_handler)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")

    window = widget_factory()
    window.setWindowTitle(title)
    window.resize(*size)
    window.show()

    return app.exec()
