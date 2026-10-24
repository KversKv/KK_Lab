#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)
from resource_path import get_resource_base
from ui.utils.icon_utils import tinted_svg_icon
from ui.widgets.toast_notification import ToastNotification
from ui.pages.n6705c_power_analyzer.datalog.datalog_ui import N6705CDatalogUI
from ui.pages.n6705c_power_analyzer.datalog.helpers import _make_svg_icon
from log_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# 独立运行（python n6705c_datalog_ui.py）专用：无边框窗口 + 自建标题栏
# 方案与 ui/main_window.py 一致：Win32 下保留原生 WS_CAPTION / WS_THICKFRAME，
# WM_NCCALCSIZE 返回 0 抹掉原生非客户区，标题栏自绘；原生边框缩放 / Aero Snap 保留。
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


# 32px 内容区 + 1px 底部分隔线（QSS 盒模型：border 计入总高）
_TITLE_BAR_HEIGHT = 33


_CAPTURE_ICON_SVG = os.path.join(
    get_resource_base(), "resources", "icons_svg", "window", "scissors.svg"
)


# 控件高度单一权威：标题栏内按钮用 ID 选择器钉死尺寸，不写裸 QPushButton 规则
_TITLE_BAR_STYLE = """
QWidget#standaloneTitleBar {
    background-color: #121417;
    border-bottom: 1px solid #1a2b52;
}
QWidget#standaloneTitleBar QLabel {
    background: transparent;
    border: none;
}
QLabel#standaloneTitleText {
    color: #e6eeff;
    font-family: "Segoe UI Variable Text", "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
    background: transparent;
    border: none;
}
QPushButton#captureChartBtn {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    border: none;
    border-radius: 3px;
    background-color: transparent;
}
QPushButton#captureChartBtn:hover {
    background-color: #1b2640;
}
QPushButton#captureChartBtn:pressed {
    background-color: #2563eb;
}
QPushButton#waveformSummaryBtn {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    border: none;
    border-radius: 3px;
    background-color: transparent;
}
QPushButton#waveformSummaryBtn:hover {
    background-color: #1b2640;
}
QPushButton#waveformSummaryBtn:pressed {
    background-color: #2563eb;
}
QFrame#titleBarSeparator {
    background-color: #2a3a5f;
    border: none;
}
QPushButton#labelsToggleBtn {
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    padding: 0px;
    border: none;
    border-radius: 3px;
    background-color: transparent;
}
QPushButton#labelsToggleBtn:hover {
    background-color: #1b2640;
}
QPushButton#labelsToggleBtn:checked {
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


class _StandaloneTitleBar(QWidget):
    """独立运行态自建标题栏：图标 + 标题 + 一键截图 + 窗口控制按钮（仿 ui/app_top_bar.py）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("standaloneTitleBar")
        self.setFixedHeight(_TITLE_BAR_HEIGHT)
        self.setStyleSheet(_TITLE_BAR_STYLE)
        # 纯 QWidget 默认不绘制 QSS 背景（会透出父级底色），须显式打开
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._drag_origin = None

        from ui.app_top_bar import _caption_icon
        self._caption_icon = _caption_icon

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(8)

        icon_label = QLabel(self)
        icon_label.setFixedSize(16, 16)
        icon_label.setPixmap(_make_svg_icon("sparkles.svg", "#d4a514", 16).pixmap(16, 16))
        layout.addWidget(icon_label, 0, Qt.AlignVCenter)

        title_label = QLabel("N6705C Datalog", self)
        title_label.setObjectName("standaloneTitleText")
        layout.addWidget(title_label, 0, Qt.AlignVCenter)

        layout.addStretch(1)

        # 一键截图按钮：Datalog + MEASUREMENT + Channel Config 区域 → 系统剪贴板（宿主窗口连接处理槽）
        self.capture_button = QPushButton(self)
        self.capture_button.setObjectName("captureChartBtn")
        self.capture_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.capture_button.setFocusPolicy(Qt.NoFocus)
        self.capture_button.setToolTip("截图图表/测量/通道配置区域并复制到剪贴板")
        if os.path.isfile(_CAPTURE_ICON_SVG):
            self.capture_button.setIcon(tinted_svg_icon(_CAPTURE_ICON_SVG, "#c6d4f2", 16))
            self.capture_button.setIconSize(QSize(16, 16))
        layout.addWidget(self.capture_button, 0, Qt.AlignVCenter)

        # 导出波形摘要按钮：平直线段示意图 + 阶段汇总表 → 系统剪贴板（宿主窗口连接处理槽）
        self.summary_button = QPushButton(self)
        self.summary_button.setObjectName("waveformSummaryBtn")
        self.summary_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.summary_button.setFocusPolicy(Qt.NoFocus)
        self.summary_button.setToolTip("导出波形摘要图（阶段示意图 + 阶段汇总表）到剪贴板")
        self.summary_button.setIcon(_make_svg_icon("activity.svg", "#c6d4f2", 16))
        self.summary_button.setIconSize(QSize(16, 16))
        layout.addWidget(self.summary_button, 0, Qt.AlignVCenter)

        # 分割线 + Custom Labels 展开/折叠按钮（宿主窗口连接处理槽）
        self.labels_separator = QFrame(self)
        self.labels_separator.setObjectName("titleBarSeparator")
        self.labels_separator.setFixedSize(1, 16)
        layout.addWidget(self.labels_separator, 0, Qt.AlignVCenter)

        self.labels_button = QPushButton(self)
        self.labels_button.setObjectName("labelsToggleBtn")
        self.labels_button.setCheckable(True)
        self.labels_button.setCursor(QCursor(Qt.PointingHandCursor))
        self.labels_button.setFocusPolicy(Qt.NoFocus)
        self.labels_button.setToolTip("Custom Labels")
        self.labels_button.setIcon(_make_svg_icon("tag.svg", "#c6d4f2", 16))
        self.labels_button.setIconSize(QSize(16, 16))
        layout.addWidget(self.labels_button, 0, Qt.AlignVCenter)

        layout.addSpacing(6)

        self._min_btn = self._make_caption_button("winCtrlBtn", "min", "最小化", self._on_minimize)
        layout.addWidget(self._min_btn, 0, Qt.AlignVCenter)

        self._max_btn = self._make_caption_button("winCtrlBtn", "max", "最大化", self._on_toggle_max)
        layout.addWidget(self._max_btn, 0, Qt.AlignVCenter)

        self._close_btn = self._make_caption_button("winCloseBtn", "close", "关闭", self._on_close)
        layout.addWidget(self._close_btn, 0, Qt.AlignVCenter)

        self._interactive_widgets = [
            self.capture_button,
            self.summary_button,
            self.labels_button,
            self._min_btn,
            self._max_btn,
            self._close_btn,
        ]

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


class _StandaloneDatalogWindow(N6705CDatalogUI):
    """独立运行窗口：无边框 + 自建标题栏（含一键截图），几何记忆沿用页面实现。"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if sys.platform == "win32":
            self.setWindowFlags(Qt.Window)
        else:
            self.setWindowFlags(Qt.FramelessWindowHint)
        self._resize_border = 6
        self.setMouseTracking(True)
        self.setMinimumSize(720, 480)
        self._dwm_applied = False

        self._title_bar = _StandaloneTitleBar(self)
        self._title_bar.capture_button.clicked.connect(self._on_capture_chart)
        self._title_bar.summary_button.clicked.connect(self._on_export_waveform_summary)
        self._title_bar.labels_button.clicked.connect(self.set_labels_panel_visible)
        self.labels_panel_toggled.connect(self._title_bar.labels_button.setChecked)
        # 标题栏全宽顶格（去掉 root_layout 8px 边距在标题栏四周造成的空隙）；
        # 原 8px 页面边距移交内容子布局，页面内容视觉保持不变
        root_layout = self.layout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.insertWidget(0, self._title_bar)
        last_index = root_layout.count() - 1
        for index in range(1, root_layout.count()):
            child_layout = root_layout.itemAt(index).layout()
            if child_layout is None:
                continue
            child_layout.setContentsMargins(
                8, 2 if index == 1 else 0, 8, 8 if index == last_index else 0
            )

    # ---- 一键截图：get_capture_pixmap() → 系统剪贴板 ----
    def _on_capture_chart(self):
        try:
            pixmap = self.get_capture_pixmap()
        except Exception:
            logger.error("图表截图复制到剪贴板失败", exc_info=True)
            self._show_capture_toast("截图失败，请查看日志", ToastNotification.TYPE_ERROR)
            return
        if not isinstance(pixmap, QPixmap) or pixmap.isNull():
            self._show_capture_toast("当前无可截图区域", ToastNotification.TYPE_ERROR)
            return
        try:
            QApplication.clipboard().setPixmap(pixmap)
        except Exception:
            logger.error("图表截图复制到剪贴板失败", exc_info=True)
            self._show_capture_toast("截图失败，请查看日志", ToastNotification.TYPE_ERROR)
            return
        self._show_capture_toast("图表区域已复制到剪贴板", ToastNotification.TYPE_SUCCESS)

    # ---- 导出波形摘要：get_waveform_summary_pixmap() → 系统剪贴板 ----
    def _on_export_waveform_summary(self):
        try:
            pixmap = self.get_waveform_summary_pixmap()
        except Exception:
            logger.error("波形摘要图生成失败", exc_info=True)
            self._show_capture_toast("波形摘要导出失败，请查看日志", ToastNotification.TYPE_ERROR)
            return
        if not isinstance(pixmap, QPixmap) or pixmap.isNull():
            self._show_capture_toast("当前无波形数据可摘要", ToastNotification.TYPE_ERROR)
            return
        try:
            QApplication.clipboard().setPixmap(pixmap)
        except Exception:
            logger.error("波形摘要图复制到剪贴板失败", exc_info=True)
            self._show_capture_toast("波形摘要导出失败，请查看日志", ToastNotification.TYPE_ERROR)
            return
        self._show_capture_toast("波形摘要图已复制到剪贴板", ToastNotification.TYPE_SUCCESS)

    def _show_capture_toast(self, message, toast_type):
        if not hasattr(self, "_capture_toast"):
            self._capture_toast = ToastNotification()
        self._capture_toast.show_toast(message, toast_type, self)

    # ---- 无边框窗口（Win32 原生非客户区抹除 + 自绘 caption）----
    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32" and not self._dwm_applied:
            self._enable_native_window_frame()
            self._apply_dwm_round_corners()
            self._dwm_applied = True

    def changeEvent(self, event):
        super().changeEvent(event)
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
