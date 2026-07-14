# I2C 控制模块框架（独立运行 Demo）
#python -m ui.modules.IIC_Module.i2c_module_frame

import os
import sys

if __name__ == "__main__" and __package__ in (None, ""):
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtWidgets import QWidget, QVBoxLayout
from log_config import get_logger

from ui.modules.IIC_Module.i2c_mixin import I2cMixin
from ui.modules.IIC_Module.i2c_styles import _I2C_DARK_STYLE

logger = get_logger(__name__)


class _DemoI2cWidget(I2cMixin, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_i2c()
        self.setStyleSheet(_I2C_DARK_STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)
        self.build_i2c_widgets(root)
        self.bind_i2c_signals()

    def closeEvent(self, event):
        try:
            self.close_i2c()
        except Exception:
            logger.error("I2C close failed", exc_info=True)
        super().closeEvent(event)


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from ui.standalone import resize_and_center_window

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = _DemoI2cWidget()
    w.setWindowTitle("I2C 控制台")
    resize_and_center_window(w, size=(960, 760))
    w.show()
    sys.exit(app.exec())
