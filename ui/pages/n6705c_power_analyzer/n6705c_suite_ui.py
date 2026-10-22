#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# run cmd:
# python ui\pages\n6705c_power_analyzer\n6705c_suite_ui.py

import sys
import os

if __name__ == "__main__" and __package__ in (None, ""):
    _PROJECT_ROOT = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

from ui.resource_path import get_resource_base

sys.path.append(get_resource_base())

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QButtonGroup, QApplication,
)
from PySide6.QtCore import Qt, Signal, QSize, QEvent, QCoreApplication
from PySide6.QtGui import QPixmap, QCursor, QCloseEvent

from log_config import get_logger
from ui.utils.icon_utils import tinted_svg_icon
from ui.widgets.toast_notification import ToastNotification
from ui.pages.n6705c_power_analyzer.n6705c_top import N6705CTop
from ui.pages.n6705c_power_analyzer.n6705c_analyser_ui import N6705CAnalyserUI
from ui.pages.n6705c_power_analyzer.n6705c_datalog_ui import N6705CDatalogUI

logger = get_logger(__name__)


# 页面注册表：(key, 标题栏 tab 文案, 页面类)；后续新增界面在此追加即可
_SUITE_PAGES = [
    ("analyser", "Analyser", N6705CAnalyserUI),
    ("datalog", "Datalog", N6705CDatalogUI),
]

_TITLE_BAR_HEIGHT = 32
_APP_ICON_SVG = os.path.join(
    get_resource_base(), "resources", "icons_svg", "ai", "sparkles.svg"
)
_CAPTURE_ICON_SVG = os.path.join(
    get_resource_base(), "resources", "icons_svg", "window", "capture.svg"
)

# 控件高度单一权威：标题栏内按钮用 ID 选择器钉死尺寸，不写裸 QPushButton 规则；
# tab active/inactive 的 padding/border 盒模型一致（03§25），仅换色不改尺寸
_TITLE_BAR_STYLE = """
QWidget#suiteTitleBar {
    background-color: #020817;
}
QWidget#suiteTitleBar QLabel {
    background: transparent;
    border: none;
}
QLabel#suiteTitleText {
    color: #c6d4f2;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 1px;
    background: transparent;
    border: none;
}
QPushButton#suitePageTab {
    min-height: 22px;
    max-height: 22px;
    padding: 0px 14px;
    border: 1px solid transparent;
    border-radius: 6px;
    background-color: transparent;
    color: #8ea2c9;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#suitePageTab:hover {
    background-color: #1b2640;
    color: #c6d4f2;
}
QPushButton#suitePageTab:checked {
    background-color: #2563eb;
    border: 1px solid #2563eb;
    color: #ffffff;
}
QPushButton#captureChartBtn {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
}
QPushButton#captureChartBtn:hover {
    background-color: #1b2640;
}
QPushButton#captureChartBtn:pressed {
    background-color: #2563eb;
}
QPushButton#winCtrlBtn,
QPushButton#winCloseBtn {
    min-width: 46px;
    max-width: 46px;
    min-height: 32px;
    max-height: 32px;
    padding: 0px;
    border: none;
    border-radius: 0px;
    background-color: transparent;
}
QPushButton#winCtrlBtn:hover {
    background-color: #1b2640;
}
QPushButton#winCloseBtn:hover {
    background-color: #e81123;
}
"""


class _SuiteTitleBar(QWidget):
    """自建标题栏：图标 + 标题 + 页面切换 tab + 一键截图 + 窗口控制按钮。

    standalone=False（嵌入 MainWindow）时仅保留页面切换 tab，
    窗口控制 / 截图 / 图标 / 标题由宿主顶栏提供。
    """

    page_switch_requested = Signal(str)

    def __init__(self, pages, standalone=True, parent=None):
        super().__init__(parent)
        self.setObjectName("suiteTitleBar")
        self.setFixedHeight(_TITLE_BAR_HEIGHT)
        self.setStyleSheet(_TITLE_BAR_STYLE)
        self._drag_origin = None
        self._standalone = standalone

        from ui.app_top_bar import _caption_icon
        self._caption_icon = _caption_icon

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(8)

        self._icon_label = QLabel(self)
        self._icon_label.setFixedSize(16, 16)
        if os.path.isfile(_APP_ICON_SVG):
            self._icon_label.setPixmap(
                tinted_svg_icon(_APP_ICON_SVG, "#d4a514", 16).pixmap(16, 16)
            )
        layout.addWidget(self._icon_label, 0, Qt.AlignVCenter)

        self._title_label = QLabel("N6705C Suite", self)
        self._title_label.setObjectName("suiteTitleText")
        layout.addWidget(self._title_label, 0, Qt.AlignVCenter)

        layout.addSpacing(12)

        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tab_buttons = {}
        for key, text in pages:
            btn = QPushButton(text, self)
            btn.setObjectName("suitePageTab")
            btn.setCheckable(True)
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setFocusPolicy(Qt.NoFocus)
            btn.clicked.connect(lambda _checked=False, k=key: self._on_tab_clicked(k))
            self._tab_group.addButton(btn)
            self._tab_buttons[key] = btn
            layout.addWidget(btn, 0, Qt.AlignVCenter)

        layout.addStretch(1)

        # 一键截图按钮：当前页图表区域 → 系统剪贴板（宿主窗口连接处理槽）
        self.capture_button = QPushButton(self)
        self.capture_button.setObjectName("captureChartBtn")
        self.capture_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.capture_button.setFocusPolicy(Qt.NoFocus)
        self.capture_button.setToolTip("截图当前页图表区域并复制到剪贴板")
        if os.path.isfile(_CAPTURE_ICON_SVG):
            self.capture_button.setIcon(tinted_svg_icon(_CAPTURE_ICON_SVG, "#c6d4f2", 16))
            self.capture_button.setIconSize(QSize(16, 16))
        layout.addWidget(self.capture_button, 0, Qt.AlignVCenter)

        layout.addSpacing(6)

        self._min_btn = self._make_caption_button("winCtrlBtn", "min", "最小化", self._on_minimize)
        layout.addWidget(self._min_btn, 0, Qt.AlignVCenter)

        self._max_btn = self._make_caption_button("winCtrlBtn", "max", "最大化", self._on_toggle_max)
        layout.addWidget(self._max_btn, 0, Qt.AlignVCenter)

        self._close_btn = self._make_caption_button("winCloseBtn", "close", "关闭", self._on_close)
        layout.addWidget(self._close_btn, 0, Qt.AlignVCenter)

        if not standalone:
            for w in (self._icon_label, self._title_label,
                      self.capture_button,
                      self._min_btn, self._max_btn, self._close_btn):
                w.hide()

        self._interactive_widgets = list(self._tab_buttons.values()) + [
            self.capture_button,
            self._min_btn,
            self._max_btn,
            self._close_btn,
        ]

    def _on_tab_clicked(self, key):
        self.page_switch_requested.emit(key)

    def set_current_page(self, key):
        btn = self._tab_buttons.get(key)
        if btn is not None and not btn.isChecked():
            btn.setChecked(True)

    def _make_caption_button(self, object_name, kind, tooltip, slot):
        btn = QPushButton(self)
        btn.setObjectName(object_name)
        btn.setIcon(self._caption_icon(kind))
        btn.setIconSize(QSize(12, 12))
        btn.setCursor(QCursor(Qt.ArrowCursor))
        btn.setToolTip(tooltip)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.clicked.connect(slot)
        return btn

    def sync_max_icon(self):
        win = self.window()
        if win is not None and win.isMaximized():
            self._max_btn.setIcon(self._caption_icon("restore"))
            self._max_btn.setToolTip("还原")
        else:
            self._max_btn.setIcon(self._caption_icon("max"))
            self._max_btn.setToolTip("最大化")

    def _on_minimize(self):
        win = self.window()
        if win is not None:
            win.showMinimized()

    def _on_toggle_max(self):
        win = self.window()
        if win is None:
            return
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()
        self.sync_max_icon()

    def _on_close(self):
        win = self.window()
        if win is not None:
            win.close()

    def is_caption_window_point(self, win_x, win_y, dpr) -> bool:
        """判断窗口内物理偏移坐标是否落在标题栏可拖动区域（不在交互控件上）。"""
        dpr = dpr or 1.0
        window = self.window()
        for widget in self._interactive_widgets:
            if widget is None or not widget.isVisible():
                continue
            top_left = widget.mapTo(window, widget.rect().topLeft())
            left = top_left.x() * dpr
            top = top_left.y() * dpr
            right = left + widget.width() * dpr
            bottom = top + widget.height() * dpr
            if left <= win_x <= right and top <= win_y <= bottom:
                return False
        return True

    # 非 Win32（FramelessWindowHint 无原生 caption）下的拖动 / 双击最大化兜底
    def mousePressEvent(self, event):
        if sys.platform == "win32":
            super().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton and self.window() is not None:
            self._drag_origin = (
                event.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if sys.platform == "win32":
            super().mouseMoveEvent(event)
            return
        if self._drag_origin is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_origin)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_origin = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if sys.platform == "win32":
            super().mouseDoubleClickEvent(event)
            return
        if event.button() == Qt.LeftButton:
            self._on_toggle_max()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


# ---------------------------------------------------------------------------
# 无边框窗口：方案与 ui/main_window.py、n6705c_datalog_ui.py 独立运行态一致——
# Win32 下保留原生 WS_CAPTION / WS_THICKFRAME，WM_NCCALCSIZE 返回 0 抹掉原生
# 非客户区，标题栏自绘；原生边框缩放 / Aero Snap 保留。
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    import ctypes
    import ctypes.wintypes

    _WM_NCHITTEST = 0x0084
    _WM_NCCALCSIZE = 0x0083
    _WM_GETMINMAXINFO = 0x0024
    _WM_SYSCOMMAND = 0x0112
    _WM_NCRBUTTONUP = 0x00A5
    _TPM_RETURNCMD = 0x0100
    _TPM_LEFTALIGN = 0x0000
    _TPM_TOPALIGN = 0x0000
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
    _SWP_NOSIZE = 0x0001
    _SWP_NOMOVE = 0x0002
    _SWP_NOZORDER = 0x0004
    _SWP_NOACTIVATE = 0x0010
    _SWP_FRAMECHANGED = 0x0020

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

    _DWMWA_WINDOW_CORNER_PREFERENCE = 33
    _DWMWA_BORDER_COLOR = 34
    _DWMWCP_ROUND = 2
    _WINDOW_BORDER_COLOR = 0x00403420  # COLORREF 0x00BBGGRR -> 边框 #203440


class N6705CSuiteWindow(QWidget):
    """N6705C 套件窗口：无边框 + 自建标题栏（含页面切换 tab），
    QStackedWidget 承载多页面，共享同一 N6705CTop / InstrumentManager。

    standalone=True  独立运行：无边框顶层窗口，标题栏含窗口控制；
    standalone=False 嵌入 MainWindow：普通子部件，标题栏仅保留切换 tab，
                     截图走 MainWindow 顶栏降级链（经 get_capture_pixmap 代理）。
    """

    page_changed = Signal(str)

    def __init__(self, n6705c_top=None, instrument_manager=None,
                 ui_action_registry=None, standalone=True, parent=None):
        super().__init__(parent)
        self.setObjectName("n6705cSuiteWindow")
        self._standalone = standalone
        if standalone:
            if sys.platform == "win32":
                self.setWindowFlags(Qt.Window)
            else:
                self.setWindowFlags(Qt.FramelessWindowHint)
            self.setMouseTracking(True)
            self.setMinimumSize(960, 600)
        self._resize_border = 6
        self._dwm_applied = False
        self.setStyleSheet(
            "QWidget#n6705cSuiteWindow { background-color: #020817; }"
        )

        # 连接状态共享中枢：传入 manager 而未传 top 时自建并托管，供全部子页注入
        if n6705c_top is None and instrument_manager is not None:
            n6705c_top = N6705CTop(self)
            n6705c_top.set_instrument_manager(instrument_manager)
        self._top = n6705c_top
        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._title_bar = _SuiteTitleBar(
            [(key, text) for key, text, _cls in _SUITE_PAGES],
            standalone=standalone, parent=self,
        )
        self._title_bar.page_switch_requested.connect(self.switch_page)
        self._title_bar.capture_button.clicked.connect(self._on_capture_current_page)
        root_layout.addWidget(self._title_bar)

        self._stack = QStackedWidget(self)
        root_layout.addWidget(self._stack, 1)

        self._pages = {}
        for key, _text, page_cls in _SUITE_PAGES:
            page = page_cls(
                n6705c_top=self._top,
                instrument_manager=self._instrument_manager,
                ui_action_registry=self._ui_action_registry,
            )
            self._pages[key] = page
            self._stack.addWidget(page)

        first_key = _SUITE_PAGES[0][0]
        self._stack.setCurrentWidget(self._pages[first_key])
        self._title_bar.set_current_page(first_key)

    # ---- 页面访问 ----
    def page(self, key):
        return self._pages.get(key)

    @property
    def analyser_page(self):
        return self._pages.get("analyser")

    @property
    def datalog_page(self):
        return self._pages.get("datalog")

    # ---- 页面切换 ----
    def switch_page(self, key):
        page = self._pages.get(key)
        if page is None:
            logger.warning("未知套件页面 key: %s", key)
            return
        if page is self._stack.currentWidget():
            self._title_bar.set_current_page(key)
            return
        self._stack.setCurrentWidget(page)
        self._title_bar.set_current_page(key)
        self.page_changed.emit(key)

    def current_page_key(self):
        for key, page in self._pages.items():
            if page is self._stack.currentWidget():
                return key
        return None

    # ---- 一键截图：当前页 get_capture_pixmap() → 系统剪贴板 ----
    def get_capture_pixmap(self):
        """MainWindow 顶栏截图降级链入口：代理到当前 tab 子页。"""
        page = self._stack.currentWidget()
        grabber = getattr(page, "get_capture_pixmap", None)
        if callable(grabber):
            return grabber()
        return None

    def _on_capture_current_page(self):
        pixmap = None
        page = self._stack.currentWidget()
        grabber = getattr(page, "get_capture_pixmap", None)
        if not callable(grabber):
            self._show_capture_toast("当前页面不支持一键截图", ToastNotification.TYPE_ERROR)
            return
        try:
            pixmap = grabber()
        except Exception:
            logger.error("页面截图复制到剪贴板失败", exc_info=True)
            self._show_capture_toast("截图失败，请查看日志", ToastNotification.TYPE_ERROR)
            return
        if not isinstance(pixmap, QPixmap) or pixmap.isNull():
            self._show_capture_toast("当前无可截图区域", ToastNotification.TYPE_ERROR)
            return
        try:
            QApplication.clipboard().setPixmap(pixmap)
        except Exception:
            logger.error("页面截图复制到剪贴板失败", exc_info=True)
            self._show_capture_toast("截图失败，请查看日志", ToastNotification.TYPE_ERROR)
            return
        self._show_capture_toast("图表区域已复制到剪贴板", ToastNotification.TYPE_SUCCESS)

    def _show_capture_toast(self, message, toast_type):
        if not hasattr(self, "_capture_toast"):
            self._capture_toast = ToastNotification()
        self._capture_toast.show_toast(message, toast_type, self)

    def closeEvent(self, event):
        # 逐页显式派发 QCloseEvent 复用其 closeEvent 清理（停 poller / 采集线程）；
        # QStackedWidget 非当前页不可见、close() 不会派发事件，故用 sendEvent；
        # 嵌入态 isWindow()=False，datalog 的几何记忆保存会空转，不污染独立运行记忆
        for page in self._pages.values():
            try:
                QCoreApplication.sendEvent(page, QCloseEvent())
            except Exception:
                logger.debug("子页面关闭清理失败", exc_info=True)
        super().closeEvent(event)

    # ---- 无边框窗口（Win32 原生非客户区抹除 + 自绘 caption）----
    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32" and self.isWindow() and not self._dwm_applied:
            self._enable_native_window_frame()
            self._apply_dwm_round_corners()
            self._dwm_applied = True

    def changeEvent(self, event):
        super().changeEvent(event)
        if not self._standalone:
            return
        if event.type() == QEvent.WindowStateChange:
            self._title_bar.sync_max_icon()
            self._refresh_nc_frame()

    def _enable_native_window_frame(self):
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, _GWL_STYLE)
            style |= (
                _WS_CAPTION
                | _WS_THICKFRAME
                | _WS_MINIMIZEBOX
                | _WS_MAXIMIZEBOX
                | _WS_SYSMENU
            )
            user32.SetWindowLongW(hwnd, _GWL_STYLE, style)
            user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                _SWP_NOSIZE | _SWP_NOMOVE | _SWP_NOZORDER | _SWP_FRAMECHANGED,
            )
        except Exception:
            logger.debug("原生窗口样式注入失败", exc_info=True)

    def _apply_dwm_round_corners(self):
        try:
            hwnd = int(self.winId())
            dwmapi = ctypes.windll.dwmapi
            pref = ctypes.c_int(_DWMWCP_ROUND)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                _DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(pref),
                ctypes.sizeof(pref),
            )
            color = ctypes.c_uint(_WINDOW_BORDER_COLOR)
            dwmapi.DwmSetWindowAttribute(
                hwnd,
                _DWMWA_BORDER_COLOR,
                ctypes.byref(color),
                ctypes.sizeof(color),
            )
        except Exception:
            logger.debug("DWM 圆角设置失败（系统不支持，忽略）", exc_info=True)

    def _refresh_nc_frame(self):
        """窗口状态落定后强制重算非客户区（重发 WM_NCCALCSIZE），防止还原后顶部白条。"""
        if sys.platform != "win32":
            return
        try:
            ctypes.windll.user32.SetWindowPos(
                int(self.winId()), 0, 0, 0, 0, 0,
                _SWP_NOMOVE | _SWP_NOSIZE | _SWP_NOZORDER
                | _SWP_NOACTIVATE | _SWP_FRAMECHANGED,
            )
        except Exception:
            logger.debug("非客户区重算失败", exc_info=True)

    def show_system_menu(self):
        if sys.platform != "win32":
            return False
        try:
            user32 = ctypes.windll.user32
            hwnd = int(self.winId())
            hmenu = user32.GetSystemMenu(hwnd, False)
            if not hmenu:
                return False
            pt = ctypes.wintypes.POINT()
            user32.GetCursorPos(ctypes.byref(pt))
            flags = _TPM_RETURNCMD | _TPM_LEFTALIGN | _TPM_TOPALIGN
            user32.SetForegroundWindow(hwnd)
            cmd = user32.TrackPopupMenu(hmenu, flags, pt.x, pt.y, 0, hwnd, None)
            if cmd:
                user32.PostMessageW(hwnd, _WM_SYSCOMMAND, cmd, 0)
            return True
        except Exception:
            logger.debug("系统菜单弹出失败", exc_info=True)
            return False

    def nativeEvent(self, event_type, message):
        if sys.platform == "win32" and event_type == b"windows_generic_MSG":
            try:
                msg = ctypes.wintypes.MSG.from_address(int(message))
            except (TypeError, ValueError):
                return False, 0
            if msg.message == _WM_NCCALCSIZE:
                if msg.wParam:
                    if self.isMaximized():
                        # 最大化时 Windows 会把窗口外扩 resize border 厚度以隐藏边框，
                        # 返回 0（client = window rect）会使标题栏顶部被裁切，内缩补偿
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
                if self._apply_minmax_info(msg):
                    return True, 0
                return False, 0
            if msg.message == _WM_NCRBUTTONUP and msg.wParam == _HTCAPTION:
                if self.show_system_menu():
                    return True, 0
            if msg.message == _WM_NCHITTEST:
                global_x = ctypes.c_int16(msg.lParam & 0xFFFF).value
                global_y = ctypes.c_int16((msg.lParam >> 16) & 0xFFFF).value
                hit = self._hit_test_native(global_x, global_y)
                if hit is not None:
                    return True, hit
        return super().nativeEvent(event_type, message)

    def _apply_minmax_info(self, msg):
        """WM_GETMINMAXINFO：最小轨迹尺寸同步 Qt 约束；最大化限制在工作区。"""
        applied = False
        try:
            mmi = _MINMAXINFO.from_address(int(msg.lParam))
            dpr = self.devicePixelRatioF() or 1.0
            min_w = self.minimumWidth()
            min_h = self.minimumHeight()
            if min_w > 0 and min_h > 0:
                mmi.ptMinTrackSize.x = int(round(min_w * dpr))
                mmi.ptMinTrackSize.y = int(round(min_h * dpr))
                applied = True
        except Exception:
            logger.debug("最小轨迹尺寸写入失败", exc_info=True)
        return self._adjust_maximized_size(msg) or applied

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
            if not (self.isMaximized() or self._is_snapped()):
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
            bar_h = int(round(self._title_bar.height() * dpr))
            if 0 <= y <= bar_h:
                if self._title_bar.is_caption_window_point(x, y, dpr):
                    return _HTCAPTION
            return None
        except Exception:
            logger.debug("命中测试失败", exc_info=True)
            return None

    def _is_snapped(self):
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
            rect = _RECT()
            if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                return False
            work = info.rcWork
            touch_left = rect.left <= work.left
            touch_right = rect.right >= work.right
            touch_top = rect.top <= work.top
            touch_bottom = rect.bottom >= work.bottom
            full_height = touch_top and touch_bottom
            half_width = (rect.right - rect.left) < (work.right - work.left)
            return full_height and half_width and (touch_left or touch_right)
        except Exception:
            logger.debug("Snap 状态检测失败", exc_info=True)
            return False


if __name__ == "__main__":
    from PySide6.QtCore import qInstallMessageHandler, QtMsgType
    from PySide6.QtGui import QIcon

    def _msg_handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
            return

    qInstallMessageHandler(_msg_handler)
    app = QApplication(sys.argv)

    # Set application icon for taskbar and window
    _icon_path = os.path.join(get_resource_base(), "resources", "icons", "n6705c.ico")
    if os.path.exists(_icon_path):
        app.setWindowIcon(QIcon(_icon_path))

    app.setStyle("Fusion")
    app.setStyleSheet("""
        QWidget {
            background-color: #030b23;
            color: #eaf1ff;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            font-size: 14px;
        }
        QPushButton {
            border: 1px solid #555;
            border-radius: 4px;
            padding: 6px 12px;
            background-color: #32353a;
            color: #c8c8c8;
        }
        QPushButton:hover { background-color: #3a3d43; }
        QPushButton:pressed { background-color: #2a2d32; }
        QPushButton:disabled { background-color: #2a2d32; color: #666; }
        QComboBox {
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 20px 4px 8px;
            background-color: #32353a;
            color: #c8c8c8;
        }
        QComboBox QAbstractItemView {
            background-color: #32353a;
            color: #c8c8c8;
            border: 1px solid #555;
            selection-background-color: #4a4d52;
            outline: 0px;
        }
        QLineEdit {
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 8px;
            background-color: #32353a;
            color: #c8c8c8;
        }
        QLabel { color: #c8c8c8; }
        QCheckBox { color: #c8c8c8; }
        QFrame {
            border: 1px solid #333;
            border-radius: 4px;
            background-color: #020618;
        }
    """)

    from core.instruments import InstrumentManager
    _standalone_manager = InstrumentManager()
    _standalone_top = N6705CTop()
    _standalone_top.set_instrument_manager(_standalone_manager)
    app.aboutToQuit.connect(_standalone_manager.shutdown)

    w = N6705CSuiteWindow(
        n6705c_top=_standalone_top, instrument_manager=_standalone_manager
    )
    w.setWindowTitle("N6705C Suite")
    if os.path.exists(_icon_path):
        w.setWindowIcon(QIcon(_icon_path))
    w.resize(1440, 900)
    _screen_geo = app.primaryScreen().availableGeometry()
    w.move(_screen_geo.center() - w.rect().center())
    w.show()
    sys.exit(app.exec())
