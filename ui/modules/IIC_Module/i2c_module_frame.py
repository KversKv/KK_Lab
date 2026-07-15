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

from PySide6.QtCore import Qt, QSize, QRectF, QByteArray, QEvent
from PySide6.QtGui import QColor, QCursor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
)
from log_config import get_logger

from ui.modules.IIC_Module.i2c_mixin import I2cMixin
from ui.modules.IIC_Module.i2c_styles import _I2C_DARK_STYLE

logger = get_logger(__name__)


# ---- Windows 原生无边框窗口支持（参考 MainWindow 自绘标题栏做法） ----
if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    _WM_NCCALCSIZE = 0x0083
    _WM_NCHITTEST = 0x0084
    _WM_GETMINMAXINFO = 0x0024
    _HTCAPTION = 2
    _HTLEFT = 10
    _HTRIGHT = 11
    _HTTOP = 12
    _HTTOPLEFT = 13
    _HTTOPRIGHT = 14
    _HTBOTTOM = 15
    _HTBOTTOMLEFT = 16
    _HTBOTTOMRIGHT = 17
    _GWL_STYLE = -16
    _WS_CAPTION = 0x00C00000
    _WS_THICKFRAME = 0x00040000
    _WS_MINIMIZEBOX = 0x00020000
    _WS_MAXIMIZEBOX = 0x00010000
    _WS_SYSMENU = 0x00080000
    _MONITOR_DEFAULTTONEAREST = 0x00000002
    _DWMWA_WINDOW_CORNER_PREFERENCE = 33
    _DWMWA_BORDER_COLOR = 34
    _DWMWCP_ROUND = 2
    _WINDOW_BORDER_COLOR = 0x00403420

    class _RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

    class _MONITORINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_ulong),
            ("rcMonitor", _RECT),
            ("rcWork", _RECT),
            ("dwFlags", ctypes.c_ulong),
        ]

    class _MINMAXINFO(ctypes.Structure):
        _fields_ = [
            ("ptReserved", ctypes.wintypes.POINT),
            ("ptMaxSize", ctypes.wintypes.POINT),
            ("ptMaxPosition", ctypes.wintypes.POINT),
            ("ptMinTrackSize", ctypes.wintypes.POINT),
            ("ptMaxTrackSize", ctypes.wintypes.POINT),
        ]

    class _NCCALCSIZE_PARAMS(ctypes.Structure):
        _fields_ = [("rgrc", _RECT * 3)]


# ---- 标题栏 CPU 图标（lucide-cpu，替换原 "I2C" 文字徽标） ----
_CPU_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
    'fill="none" stroke="#c7d2fe" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M12 20v2"></path><path d="M12 2v2"></path>'
    '<path d="M17 20v2"></path><path d="M17 2v2"></path>'
    '<path d="M2 12h2"></path><path d="M2 17h2"></path><path d="M2 7h2"></path>'
    '<path d="M20 12h2"></path><path d="M20 17h2"></path><path d="M20 7h2"></path>'
    '<path d="M7 20v2"></path><path d="M7 2v2"></path>'
    '<rect x="4" y="4" width="16" height="16" rx="2"></rect>'
    '<rect x="8" y="8" width="8" height="8" rx="1"></rect></svg>'
)


def _render_cpu_pixmap(size=22):
    renderer = QSvgRenderer(QByteArray(_CPU_SVG.encode("utf-8")))
    if not renderer.isValid():
        return QPixmap()
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(painter)
    painter.end()
    return pm


def _caption_icon(kind, color="#c6d4f2", size=12):
    """绘制 Windows 11 风格的窗口控制图标（细线条、1px 描边、无填充）。"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    pen = QPen(QColor(color))
    pen.setWidthF(1.0)
    pen.setCosmetic(True)
    painter.setPen(pen)

    pad = 1.5
    x0, y0 = pad, pad
    x1, y1 = size - pad, size - pad
    cy = size / 2.0
    if kind == "min":
        painter.drawLine(QRectF(x0, cy, x1 - x0, 0).topLeft(),
                         QRectF(x1, cy, 0, 0).topLeft())
    elif kind == "max":
        painter.drawRect(QRectF(x0, y0, x1 - x0, y1 - y0))
    elif kind == "restore":
        off = 3.0
        rect_w = (x1 - x0) - off
        rect_h = (y1 - y0) - off
        painter.drawRect(QRectF(x0, y0 + off, rect_w, rect_h))
        painter.drawLine(QRectF(x0 + off, y0, 0, 0).topLeft(),
                         QRectF(x1, y0, 0, 0).topLeft())
        painter.drawLine(QRectF(x1, y0, 0, 0).topLeft(),
                         QRectF(x1, y1 - off, 0, 0).topLeft())
    elif kind == "close":
        painter.drawLine(QRectF(x0, y0, 0, 0).topLeft(),
                         QRectF(x1, y1, 0, 0).topLeft())
        painter.drawLine(QRectF(x1, y0, 0, 0).topLeft(),
                         QRectF(x0, y1, 0, 0).topLeft())
    painter.end()
    return QIcon(pixmap)


# Demo 专属样式：导航栏降级为全宽自绘标题栏 + 窗口控制按钮
_DEMO_TITLEBAR_STYLE = """
QFrame#navBar {
    background-color: #0f172a;
    border: none;
    border-bottom: 1px solid #1e293b;
    border-radius: 0px;
}
QPushButton#i2cWinBtn, QPushButton#i2cWinCloseBtn {
    min-width: 46px; max-width: 46px;
    min-height: 35px; max-height: 35px;
    padding: 0px; border: none; border-radius: 0px;
    background-color: transparent;
}
QPushButton#i2cWinBtn:hover { background-color: #1b2640; }
QPushButton#i2cWinCloseBtn:hover { background-color: #e81123; }
QWidget#i2cWinCtrlHolder { background: transparent; }
"""


class _DemoI2cWidget(I2cMixin, QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_i2c()
        # 自绘标题栏：去掉系统标题栏，导航栏充当标题栏
        self._resize_border = 6
        self._native_frame_applied = False
        self._interactive_widgets = []
        if sys.platform == "win32":
            self.setWindowFlags(Qt.Window)
        else:
            self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self.setStyleSheet(_I2C_DARK_STYLE + _DEMO_TITLEBAR_STYLE)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.build_i2c_widgets(root)
        self._restyle_for_frameless()
        self.bind_i2c_signals()

    # ---- 标题栏改造：导航栏提升为顶部全宽标题栏 ----

    def _restyle_for_frameless(self):
        outer = self.layout()
        inner = outer.itemAt(0).layout() if outer.count() else None
        if inner is None:
            return
        # 把导航栏从内容布局中提到最外层顶部，使其贴边全宽；内容区保留内边距
        nav_item = inner.takeAt(0)
        nav_bar = nav_item.widget() if nav_item is not None else None
        if nav_bar is not None:
            outer.insertWidget(0, nav_bar)
            self._nav_bar = nav_bar
        inner.setContentsMargins(10, 10, 10, 10)
        self._setup_custom_titlebar()

    def _setup_custom_titlebar(self):
        nav_bar = getattr(self, "_nav_bar", None) or self.findChild(QFrame, "navBar")
        if nav_bar is None:
            return
        self._nav_bar = nav_bar
        nav_bar.setFixedHeight(35)
        row = nav_bar.layout()
        row.setContentsMargins(16, 0, 0, 0)

        # 1) "I2C" 文字徽标 -> CPU 图标
        badge = self.findChild(QLabel, "appBadge")
        if badge is not None:
            badge.setText("")
            badge.setPixmap(_render_cpu_pixmap(22))
            badge.setFixedSize(24, 24)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet("background:transparent; border:none;")

        # 2) 窗口控制按钮（最小化 / 最大化-还原 / 关闭），紧贴标题栏右侧
        self._win_min_btn = self._make_caption_button(
            "i2cWinBtn", "min", "最小化", self._on_win_minimize)
        self._win_max_btn = self._make_caption_button(
            "i2cWinBtn", "max", "最大化", self._on_win_toggle_max)
        self._win_close_btn = self._make_caption_button(
            "i2cWinCloseBtn", "close", "关闭", self._on_win_close)

        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(0, 0, 0, 0)
        ctrl_row.setSpacing(0)
        for btn in (self._win_min_btn, self._win_max_btn, self._win_close_btn):
            ctrl_row.addWidget(btn)
        ctrl_holder = QWidget()
        ctrl_holder.setObjectName("i2cWinCtrlHolder")
        ctrl_holder.setLayout(ctrl_row)
        row.addWidget(ctrl_holder)

        # 命中测试时需排除的可拖动区域内的交互控件：导航 Tab + 窗口控制按钮
        self._interactive_widgets = [
            *getattr(self, "i2c_nav_tabs", []),
            self._win_min_btn, self._win_max_btn, self._win_close_btn,
        ]
        self._sync_max_icon()

    def _make_caption_button(self, object_name, kind, tooltip, slot):
        btn = QPushButton(self)
        btn.setObjectName(object_name)
        btn.setIcon(_caption_icon(kind))
        btn.setIconSize(QSize(12, 12))
        btn.setCursor(QCursor(Qt.ArrowCursor))
        btn.setToolTip(tooltip)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.clicked.connect(slot)
        return btn

    def _on_win_minimize(self):
        self.showMinimized()

    def _on_win_toggle_max(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._sync_max_icon()

    def _on_win_close(self):
        self.close()

    def _sync_max_icon(self):
        if not hasattr(self, "_win_max_btn"):
            return
        if self.isMaximized():
            self._win_max_btn.setIcon(_caption_icon("restore"))
            self._win_max_btn.setToolTip("还原")
        else:
            self._win_max_btn.setIcon(_caption_icon("max"))
            self._win_max_btn.setToolTip("最大化")

    # ---- 无边框窗口：原生样式注入 / DWM 圆角 / 命中测试 ----

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32" and not self._native_frame_applied:
            self._enable_native_window_frame()
            self._apply_dwm_round_corners()
            self._native_frame_applied = True

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self._sync_max_icon()

    def mousePressEvent(self, event):
        # 非 Windows 平台回退：在标题栏空白区域按下左键时启动系统移动
        if (sys.platform != "win32"
                and event.button() == Qt.LeftButton
                and getattr(self, "_nav_bar", None) is not None):
            pos = event.position().toPoint()
            if pos.y() <= self._nav_bar.height() and self._is_caption_point_logical(pos):
                wh = self.windowHandle()
                if wh is not None and wh.startSystemMove():
                    return
        super().mousePressEvent(event)

    def _is_caption_point_logical(self, pos):
        for widget in self._interactive_widgets:
            if widget is None or not widget.isVisible():
                continue
            top_left = widget.mapTo(self, widget.rect().topLeft())
            rect = QRectF(top_left.x(), top_left.y(),
                          widget.width(), widget.height())
            if rect.contains(pos.x(), pos.y()):
                return False
        return True

    def _enable_native_window_frame(self):
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, _GWL_STYLE)
            style |= (
                _WS_CAPTION | _WS_THICKFRAME
                | _WS_MINIMIZEBOX | _WS_MAXIMIZEBOX | _WS_SYSMENU
            )
            user32.SetWindowLongW(hwnd, _GWL_STYLE, style)
            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020
            user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_FRAMECHANGED,
            )
        except Exception:
            logger.debug("原生窗口样式注入失败", exc_info=True)

    def _apply_dwm_round_corners(self):
        try:
            hwnd = int(self.winId())
            dwmapi = ctypes.windll.dwmapi
            pref = ctypes.c_int(_DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(
                hwnd, _DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(pref), ctypes.sizeof(pref),
            )
            color = ctypes.c_uint(_WINDOW_BORDER_COLOR)
            dwmapi.DwmSetWindowAttribute(
                hwnd, _DWMWA_BORDER_COLOR,
                ctypes.byref(color), ctypes.sizeof(color),
            )
        except Exception:
            logger.debug("DWM 圆角设置失败（系统不支持，忽略）", exc_info=True)

    def nativeEvent(self, event_type, message):
        if sys.platform == "win32" and event_type == b"windows_generic_MSG":
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
            except (TypeError, ValueError):
                return False, 0
            if msg.message == _WM_NCCALCSIZE:
                if msg.wParam:
                    if self.isMaximized():
                        params = _NCCALCSIZE_PARAMS.from_address(int(msg.lParam))
                        dpr = self.devicePixelRatioF() or 1.0
                        border = int(round(self._resize_border * dpr))
                        params.rgrc[0].left += border
                        params.rgrc[0].top += border
                        params.rgrc[0].right -= border
                        params.rgrc[0].bottom -= border
                    return True, 0
                return False, 0
            if msg.message == _WM_GETMINMAXINFO:
                if self._adjust_maximized_size(msg):
                    return True, 0
                return False, 0
            if msg.message == _WM_NCHITTEST:
                global_x = ctypes.c_int16(msg.lParam & 0xFFFF).value
                global_y = ctypes.c_int16((msg.lParam >> 16) & 0xFFFF).value
                hit = self._hit_test_native(global_x, global_y)
                if hit is not None:
                    return True, hit
        return super().nativeEvent(event_type, message)

    def _hit_test_native(self, screen_x, screen_y):
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            rect = _RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return None
            win_w = rect.right - rect.left
            win_h = rect.bottom - rect.top
            x = screen_x - rect.left
            y = screen_y - rect.top
            dpr = self.devicePixelRatioF() or 1.0
            b = int(round(self._resize_border * dpr))
            if not self.isMaximized():
                left, right = x < b, x > win_w - b
                top, bottom = y < b, y > win_h - b
                if top and left:
                    return _HTTOPLEFT
                if top and right:
                    return _HTTOPRIGHT
                if bottom and left:
                    return _HTBOTTOMLEFT
                if bottom and right:
                    return _HTBOTTOMRIGHT
                if left:
                    return _HTLEFT
                if right:
                    return _HTRIGHT
                if top:
                    return _HTTOP
                if bottom:
                    return _HTBOTTOM
            nav_bar = getattr(self, "_nav_bar", None)
            if nav_bar is not None:
                bar_h = int(round(nav_bar.height() * dpr))
                if 0 <= y <= bar_h and self._is_caption_point(x, y, dpr):
                    return _HTCAPTION
            return None
        except Exception:
            logger.debug("命中测试失败", exc_info=True)
            return None

    def _is_caption_point(self, win_x, win_y, dpr):
        for widget in self._interactive_widgets:
            if widget is None or not widget.isVisible():
                continue
            top_left = widget.mapTo(self, widget.rect().topLeft())
            left = top_left.x() * dpr
            top = top_left.y() * dpr
            right = left + widget.width() * dpr
            bottom = top + widget.height() * dpr
            if left <= win_x <= right and top <= win_y <= bottom:
                return False
        return True

    def _adjust_maximized_size(self, msg):
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            monitor = user32.MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONEAREST)
            if not monitor:
                return False
            info = _MONITORINFO()
            info.cbSize = ctypes.sizeof(_MONITORINFO)
            if not user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return False
            work = info.rcWork
            mon = info.rcMonitor
            mmi = _MINMAXINFO.from_address(int(msg.lParam))
            mmi.ptMaxPosition.x = work.left - mon.left
            mmi.ptMaxPosition.y = work.top - mon.top
            mmi.ptMaxSize.x = work.right - work.left
            mmi.ptMaxSize.y = work.bottom - work.top
            mmi.ptMaxTrackSize.x = work.right - work.left
            mmi.ptMaxTrackSize.y = work.bottom - work.top
            return True
        except Exception:
            logger.debug("最大化尺寸校正失败", exc_info=True)
            return False

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
