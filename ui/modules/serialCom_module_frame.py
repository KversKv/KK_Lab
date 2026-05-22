#
# python -m ui.modules.serialCom_module_frame
#

import os as _os
import sys as _sys
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)
from ui.resource_path import get_resource_base as _get_resource_base
from ui.resource_path import get_resource_base
_PROJECT_ROOT = _get_resource_base()
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)

import json
import os
import re
import time
import serial
import serial.tools.list_ports
from datetime import datetime

from PySide6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSizePolicy,
    QFrame, QWidget, QTextEdit, QLineEdit, QComboBox, QCheckBox,
    QScrollArea, QSplitter, QApplication, QMenu, QFileDialog, QGridLayout,
    QSpinBox, QDialog, QDialogButtonBox, QTabWidget,
    QInputDialog, QMessageBox, QTabBar,
)
import uuid as _uuid
from PySide6.QtCore import (
    Signal, QThread, QObject, QTimer, QRectF, Qt, QSize, QRect, QPoint,
    QPropertyAnimation, QEasingCurve, Property, QMimeData,
)
from PySide6.QtGui import (
    QIcon, QPainter, QPixmap, QColor, QAction, QPen, QFont,
    QShortcut, QKeySequence,
)
from PySide6.QtSvg import QSvgRenderer

from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.scrollbar import SCROLLBAR_STYLE
from debug_config import DEBUG_MOCK
from log_config import get_logger
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from core.auto_baud_detector import (
    AutoBaudState, AutoBaudMonitor, AutoBaudScanWorker,
    AUTO_BAUD_CONFIG, score_rx_data,
)


logger = get_logger(__name__)


_SVG_COMMON_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Common"
)
_SVG_SERIAL_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Serial",
)
_SVG_LOGS_DIR = os.path.join(
    get_resource_base(),
    "resources", "modules", "SVG_Logs",
)
_SEARCH_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "search.svg")
_LINK_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "link.svg")
_UNLINK_ICON_PATH = os.path.join(_SVG_COMMON_DIR, "unlink.svg")

_SERIAL_BTN_HEIGHT = 26
_SERIAL_BTN_ICON_SIZE = 14
_SERIAL_BTN_RADIUS = 6
_TERM_FONT = '"JetBrains Mono", "Fira Code", Consolas, "Menlo", "Courier New", monospace'
_UI_FONT = '"Inter", "PingFang SC", "Microsoft YaHei", "Segoe UI", -apple-system, sans-serif'

# --- Color Palette (Serial Log 配色规范) ---
_CLR_BG_MAIN       = "#020618"  # 主背景
_CLR_BG_PANEL      = "#020618"  # 配置面板/工具栏背景
_CLR_BG_LOG        = "#020618"  # 日志/输入框背景（凹陷区）
_CLR_BORDER        = "#1E293B"  # 分隔线与边框
_CLR_BORDER_HOVER  = "#475569"  # hover 态边框 / 滚动条悬停
_CLR_TEXT_TITLE    = "#F8FAFC"  # 最大标题（Serial Log）
_CLR_TEXT_ACCENT   = "#FBBF24"  # Quick Commands 标题 / WARNING
_CLR_TEXT_SUBTITLE = "#93C5FD"  # 次级标题（Serial Config 等）/ INFO
_CLR_TEXT_LABEL    = "#93C5FD"  # 表单标签 / INFO
_CLR_TEXT_BTN      = "#93C5FD"  # 工具栏按钮 / INFO
_CLR_TEXT_BTN_LOG  = "#CBD5E1"  # 日志区按钮 / RX 正文
_CLR_TEXT_BODY     = "#CBD5E1"  # 日志正文 / RX
_CLR_TEXT_TIME     = "#64748B"  # 日志时间戳
_CLR_TEXT_LINENO   = "#475569"  # 行号
_CLR_TEXT_INFO     = "#93C5FD"  # [INFO] / 串口工具自身信息
_CLR_INPUT_BG      = "#0F172A"  # 输入框背景
_CLR_INPUT_TEXT    = "#E2E8F0"  # 输入框文字
_CLR_CURSOR        = "#38BDF8"  # 光标
_CLR_SELECTION_BG  = "#1E3A5F"  # 选中背景
_CLR_SELECTION_TEXT= "#F8FAFC"  # 选中文字
_CLR_SCROLLBAR     = "#334155"  # 滚动条滑块
_CLR_SCROLLBAR_HV  = "#475569"  # 滚动条悬停
_CLR_CONNECT_FG    = "#5EEAD4"  # Connect / TX
_CLR_CONNECT_BG    = "#07202b"  # Connect 背景
_CLR_SEND_BG       = "#5EEAD4"  # Send / TX
_CLR_SEND_HOVER    = "#2DD4BF"  # Send hover (teal-400)
_CLR_SEND_PRESS    = "#14B8A6"  # Send pressed (teal-500)
_CLR_WARNING       = "#FBBF24"  # WARNING / 警告内容
_CLR_ERROR         = "#F87171"  # ERROR / 断开/错误
_CLR_RX            = "#CBD5E1"  # RX / UART 接收正文
_CLR_TX            = "#5EEAD4"  # TX / 发送给 UART 的内容
_CLR_FILTER_TEXT   = "#EDE9FE"  # 筛选命中文字
_CLR_FILTER_BG     = "#312E81"  # 筛选命中背景
_CLR_FILTER_BORDER = "#818CF8"  # 筛选高亮边框
_CLR_TOGGLE_ON     = "#818CF8"  # ASCII/HEX 选中 / FILTER 边框


def _serial_search_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: transparent;
            border: 1px solid #1e293b;
            border-radius: {r}px;
            color: #94a3b8;
            font-family: {_UI_FONT};
            font-size: 12px;
            font-weight: 500;
            min-height: {h}px;
        }}
        QPushButton:hover {{
            border: 1px solid #334155;
            color: #cbd5e1;
        }}
        QPushButton:pressed {{
            background-color: #050b1e;
        }}
        QPushButton:disabled {{
            background-color: transparent;
            color: #64748b;
            border: 1px solid #1e293b;
        }}
    """


def _serial_connect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: #07202b;
            border: none;
            border-radius: {r}px;
            color: #34d399;
            font-family: {_UI_FONT};
            font-size: 12px;
            font-weight: 700;
            min-height: {h}px;
            min-width: 96px;
        }}
        QPushButton:hover {{
            background-color: #0a2d3b;
        }}
        QPushButton:pressed {{
            background-color: #051820;
        }}
        QPushButton:disabled {{
            background-color: #050b1e;
            color: #64748b;
            border: none;
        }}
    """


def _serial_disconnect_style(h=_SERIAL_BTN_HEIGHT, r=_SERIAL_BTN_RADIUS):
    return f"""
        QPushButton {{
            background-color: #2b0a12;
            border: none;
            border-radius: {r}px;
            color: #f43f5e;
            font-family: {_UI_FONT};
            font-size: 12px;
            font-weight: 700;
            min-height: {h}px;
            min-width: 96px;
        }}
        QPushButton:hover {{
            background-color: #3a0f14;
        }}
        QPushButton:pressed {{
            background-color: #1f060b;
        }}
        QPushButton:disabled {{
            background-color: #050b1e;
            color: #64748b;
            border: none;
        }}
    """


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


MODE_SEARCH_SELECT = "search_and_select"
MODE_FULL = "full"
MODE_INLINE = "inline"


class SerialComMixin:
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    def init_serial_connection(self, mode=MODE_FULL, baudrate=115200, prefix="Serial"):
        self._serial_mode = mode
        self._serial_baudrate = baudrate
        self._serial_prefix = prefix
        self._serial_port = None
        self._serial_conn = None
        self._serial_connected = False
        self._serial_search_thread = None
        self._serial_search_worker = None
        self._serial_read_thread = None
        self._serial_read_worker = None
        self._serial_btn_height = _SERIAL_BTN_HEIGHT
        self._serial_btn_radius = _SERIAL_BTN_RADIUS
        self._serial_btn_icon_size = _SERIAL_BTN_ICON_SIZE

    def build_serial_connection_widgets(self, layout,
                                        btn_height=_SERIAL_BTN_HEIGHT,
                                        btn_radius=_SERIAL_BTN_RADIUS,
                                        btn_icon_size=_SERIAL_BTN_ICON_SIZE):
        self._serial_btn_height = btn_height
        self._serial_btn_radius = btn_radius
        self._serial_btn_icon_size = btn_icon_size

        if self._serial_mode == MODE_INLINE:
            _inline_h = 22
            _inline_icon = 12
            _inline_r = 4

            row = QHBoxLayout()
            row.setSpacing(6)
            row.setContentsMargins(0, 0, 0, 0)

            self.serial_label = QLabel("COM:")
            self.serial_label.setStyleSheet(
                f"font-size: 12px; color: #94a3b8; background: transparent; border: none; font-family: {_UI_FONT};"
            )
            row.addWidget(self.serial_label)

            self.serial_combo = DarkComboBox()
            self.serial_combo.setSizeAdjustPolicy(
                DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            self.serial_combo.setMinimumContentsLength(10)
            self.serial_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.serial_combo.setFixedHeight(_inline_h)
            _font = self.serial_combo.font()
            _font.setPixelSize(12)
            self.serial_combo.setFont(_font)
            row.addWidget(self.serial_combo, 1)

            self.serial_search_btn = _SerialSearchButton(
                icon_size=_inline_icon,
                btn_height=_inline_h,
                btn_radius=_inline_r,
            )
            self.serial_search_btn.setFixedSize(_inline_h, _inline_h)
            self.serial_search_btn.setStyleSheet(
                self.serial_search_btn.styleSheet() + f"""
                QPushButton {{
                    padding: 0px;
                    margin: 0px;
                    min-width: {_inline_h}px;
                    max-width: {_inline_h}px;
                    min-height: {_inline_h}px;
                    max-height: {_inline_h}px;
                }}
            """
            )
            row.addWidget(self.serial_search_btn)

            layout.addLayout(row)
            return

        self.serial_status_label = QLabel("● Not Connected")
        self.serial_status_label.setObjectName("statusErr")
        layout.addWidget(self.serial_status_label)

        self.serial_combo = DarkComboBox()
        self.serial_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.serial_combo.setMinimumContentsLength(10)
        self.serial_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(self.serial_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        btn_row.setContentsMargins(0, 2, 0, 0)

        self.serial_search_btn = _SerialSearchButton(
            icon_size=btn_icon_size,
            btn_height=btn_height,
            btn_radius=btn_radius,
        )
        btn_row.addWidget(self.serial_search_btn)

        if self._serial_mode == MODE_FULL:
            self.serial_connect_btn = QPushButton()
            _update_serial_btn_state(
                self.serial_connect_btn, connected=False,
                h=btn_height, r=btn_radius, icon_size=btn_icon_size,
            )
            btn_row.addWidget(self.serial_connect_btn)

        layout.addLayout(btn_row)

    def bind_serial_signals(self):
        self.serial_search_btn.clicked.connect(self._on_serial_search)
        if self._serial_mode == MODE_FULL and hasattr(self, 'serial_connect_btn'):
            self.serial_connect_btn.clicked.connect(self._on_serial_toggle)

    def _set_serial_status(self, text, is_error=False):
        if not hasattr(self, 'serial_status_label'):
            return
        self.serial_status_label.setText(text)
        if is_error:
            self.serial_status_label.setObjectName("statusErr")
        elif any(kw in text for kw in ["Searching", "Connecting", "Disconnecting"]):
            self.serial_status_label.setObjectName("statusWarn")
        else:
            self.serial_status_label.setObjectName("statusOk")
        self.serial_status_label.style().unpolish(self.serial_status_label)
        self.serial_status_label.style().polish(self.serial_status_label)
        self.serial_status_label.update()

    def _on_serial_search(self):
        if DEBUG_MOCK:
            self.serial_combo.clear()
            self.serial_combo.addItem("[MOCK] COM99 - Mock Serial Device")
            self._set_serial_status("● Mock port ready")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Mock port loaded.")
            return

        if self._serial_search_thread is not None and self._serial_search_thread.isRunning():
            return

        self._set_serial_status("● Searching")
        self.serial_search_btn.setEnabled(False)
        if self._serial_mode == MODE_FULL and hasattr(self, 'serial_connect_btn'):
            self.serial_connect_btn.setEnabled(False)

        worker = _SearchSerialPortWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_serial_search_done)
        worker.error.connect(self._on_serial_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_serial_search_thread_cleanup())

        self._serial_search_thread = thread
        self._serial_search_worker = worker
        thread.start()

    def _on_serial_search_thread_cleanup(self):
        self._serial_search_thread = None
        self._serial_search_worker = None

    def _on_serial_search_done(self, ports):
        self.serial_combo.clear()
        if ports:
            for port in ports:
                self.serial_combo.addItem(port)
            count = len(ports)
            self._set_serial_status(f"● Found {count} port(s)")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Found {count} serial port(s).")
        else:
            self.serial_combo.addItem("No serial ports found")
            self.serial_combo.setEnabled(False)
            self._set_serial_status("● No port found", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] No serial ports found.")

        self.serial_search_btn.setEnabled(True)
        if self._serial_mode == MODE_FULL and hasattr(self, 'serial_connect_btn'):
            self.serial_connect_btn.setEnabled(bool(ports))

    def _on_serial_search_error(self, err):
        self._set_serial_status("● Search failed", is_error=True)
        if hasattr(self, 'append_log'):
            self.append_log(f"[{self._serial_prefix}] Search error: {err}")
        self.serial_search_btn.setEnabled(True)
        if self._serial_mode == MODE_FULL and hasattr(self, 'serial_connect_btn'):
            self.serial_connect_btn.setEnabled(False)

    def _on_serial_toggle(self):
        if self._serial_connected:
            self._on_serial_disconnect()
        else:
            self._on_serial_connect()

    def get_selected_serial_port(self):
        text = self.serial_combo.currentText()
        if not text or text in ("No serial ports found",):
            return None
        return text.split()[0]

    def connect_selected_serial(self, baudrate=None):
        port = self.get_selected_serial_port()
        if port is None:
            return None
        br = baudrate if baudrate is not None else self._serial_baudrate
        try:
            conn = serial.Serial(port, br, timeout=1)
            self._serial_conn = conn
            self._serial_port = port
            self._serial_connected = True
            self.serial_connection_changed.emit(True)
            return conn
        except Exception:
            return None

    def _on_serial_connect(self):
        if self._serial_mode != MODE_FULL:
            return
        self.serial_connect_btn.setEnabled(False)

        port = self.get_selected_serial_port()
        if port is None:
            self._set_serial_status("● No valid port selected", is_error=True)
            self.serial_connect_btn.setEnabled(True)
            return

        if DEBUG_MOCK:
            self._serial_conn = None
            self._serial_port = "MOCK"
            self._serial_connected = True
            self._update_serial_connect_ui(True)
            self._set_serial_status(f"● Connected to: MOCK (DEBUG)")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Mock serial connected.")
            self.serial_connection_changed.emit(True)
            return

        self._set_serial_status("● Connecting")
        try:
            conn = serial.Serial(port, self._serial_baudrate, timeout=1)
            self._serial_conn = conn
            self._serial_port = port
            self._serial_connected = True
            self._update_serial_connect_ui(True)
            self._set_serial_status(f"● Connected to: {port}")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Connected: {port} @ {self._serial_baudrate}")
            self.serial_connection_changed.emit(True)
            self._start_serial_read()
        except Exception as e:
            self._set_serial_status("● Connection failed", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Connection failed: {e}")
        finally:
            self.serial_connect_btn.setEnabled(True)

    def _on_serial_disconnect(self):
        if self._serial_mode != MODE_FULL:
            return
        self.serial_connect_btn.setEnabled(False)
        self._stop_serial_read()
        try:
            if self._serial_conn is not None and self._serial_conn.is_open:
                self._serial_conn.close()
        except Exception as e:
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Close error: {e}")

        self._serial_conn = None
        self._serial_port = None
        self._serial_connected = False
        self._update_serial_connect_ui(False)
        self._set_serial_status("● Not Connected", is_error=True)
        if hasattr(self, 'append_log'):
            self.append_log(f"[{self._serial_prefix}] Disconnected.")
        self.serial_connection_changed.emit(False)
        self.serial_connect_btn.setEnabled(True)

    def _update_serial_connect_ui(self, connected):
        if not hasattr(self, 'serial_connect_btn'):
            return
        _update_serial_btn_state(
            self.serial_connect_btn, connected,
            h=self._serial_btn_height,
            r=self._serial_btn_radius,
            icon_size=self._serial_btn_icon_size,
        )
        self.serial_search_btn.setEnabled(not connected)
        self.serial_combo.setEnabled(not connected)

    def _start_serial_read(self):
        if self._serial_conn is None or not self._serial_conn.is_open:
            return
        if self._serial_read_thread is not None and self._serial_read_thread.isRunning():
            return

        worker = _SerialReadWorker(self._serial_conn)
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.data_received.connect(self._on_serial_data_received)
        worker.error.connect(self._on_serial_read_error)

        self._serial_read_thread = thread
        self._serial_read_worker = worker
        thread.start()

    def _stop_serial_read(self):
        if self._serial_read_worker is not None:
            self._serial_read_worker.stop()
        if self._serial_read_thread is not None and self._serial_read_thread.isRunning():
            self._serial_read_thread.quit()
            self._serial_read_thread.wait(2000)
        self._serial_read_thread = None
        self._serial_read_worker = None

    def _on_serial_data_received(self, data):
        self.serial_data_received.emit(data)

    def _on_serial_read_error(self, err):
        if hasattr(self, 'append_log'):
            self.append_log(f"[{self._serial_prefix}] Read error: {err}")

    def serial_send(self, data):
        if self._serial_conn is None or not self._serial_conn.is_open:
            return False
        try:
            if isinstance(data, str):
                data = data.encode('utf-8')
            self._serial_conn.write(data)
            return True
        except Exception as e:
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Send error: {e}")
            return False

    def get_serial_connection(self):
        return self._serial_conn

    def is_serial_connected(self):
        return self._serial_connected

    def close_serial(self):
        self._stop_serial_read()
        try:
            if self._serial_conn is not None and self._serial_conn.is_open:
                self._serial_conn.close()
        except Exception:
            pass
        self._serial_conn = None
        self._serial_port = None
        self._serial_connected = False

    # ------------------------------------------------------------------
    #  complete_serialComWidget  —  Full Serial Console Builder
    # ------------------------------------------------------------------

    def complete_serialComWidget(self, parent_layout):
        self._sc_rx_bytes = 0
        self._sc_tx_bytes = 0
        self._sc_paused = False
        self._sc_auto_scroll = True
        self._sc_rx_line_buf = ""
        self._sc_rx_flush_timer = None
        self._sc_all_logs = []
        self._sc_rx_display_hex = False
        self._sc_tx_display_hex = False
        self._sc_show_timestamp = True
        self._sc_auto_resend = False
        self._sc_resend_interval = 1000
        self._sc_line_ending = "\r\n"
        self._sc_show_send = True
        self._sc_line_by_line = False
        self._sc_send_history = []
        self._sc_quick_commands = []  # 兼容占位，已不再使用
        self._sc_qc_data = self._sc_qc_default_data()
        self._sc_sidebar_visible = True
        self._sc_extra_log_panels = []
        self._sc_active_log_panel_index = 0
        self._sc_filter_dirty = False
        self._sc_filter_last_count = 0
        self._sc_filter_applied_pattern = ""
        self._sc_filter_applied_use_regex = False
        self._sc_filter_applied_case = False
        self._sc_filter_applied_invert = False
        self._sc_filter_applied_before = 0
        self._sc_filter_applied_after = 0

        self._sc_auto_baud_monitor = AutoBaudMonitor()
        self._sc_auto_baud_monitor.enabled = True
        self._sc_auto_baud_monitor.runtime_redetect_enabled = True
        self._sc_auto_baud_scan_thread = None
        self._sc_auto_baud_scan_worker = None
        self._sc_auto_baud_pending_first_rx = False
        self._sc_auto_baud_initial_buf = bytearray()
        self._sc_auto_baud_initial_ts = 0.0

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._sc_toolbar = self._build_sc_toolbar()
        outer.addWidget(self._sc_toolbar)

        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setHandleWidth(6)
        body_splitter.setStyleSheet(f"""
            QSplitter {{ background-color: {_CLR_BG_PANEL}; }}
            QSplitter::handle {{ background-color: {_CLR_BG_PANEL}; border: none; }}
            QSplitter::handle:hover {{ background-color: #122042; }}
        """)

        self._sc_body_splitter = body_splitter
        self._sc_sidebar_default_width = 280
        self._sc_sidebar_min_width = 270
        self._sc_sidebar_widget = self._build_sc_sidebar()
        body_splitter.addWidget(self._sc_sidebar_widget)

        center_widget = QFrame()
        center_widget.setObjectName("scCenterWidget")
        center_widget.setFrameShape(QFrame.NoFrame)
        center_widget.setAutoFillBackground(True)
        center_widget.setStyleSheet(
            f"QFrame#scCenterWidget {{ "
            f"background-color: {_CLR_BG_PANEL}; "
            f"border: 1px solid #1e293b; "
            f"border-radius: 4px; "
            f"}}"
        )
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(1, 1, 1, 1)
        center_layout.setSpacing(0)

        self._sc_log_container = QWidget()
        self._sc_log_grid = QGridLayout(self._sc_log_container)
        self._sc_log_grid.setContentsMargins(0, 0, 0, 0)
        self._sc_log_grid.setSpacing(2)

        self._sc_log_area = self._build_sc_log_area()
        self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
        center_layout.addWidget(self._sc_log_container, 1)

        self._sc_send_area = self._build_sc_send_area()
        center_layout.addWidget(self._sc_send_area)

        self._sc_quick_area = self._build_sc_quick_commands()
        center_layout.addWidget(self._sc_quick_area)

        body_splitter.addWidget(center_widget)
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        body_splitter.setSizes([self._sc_sidebar_default_width, 600])

        outer.addWidget(body_splitter, 1)

        parent_layout.addLayout(outer)

        self._bind_sc_signals()

        self._sc_resend_timer = QTimer()
        self._sc_resend_timer.timeout.connect(self._sc_on_resend_tick)

        self._sc_pending_html = []
        self._sc_flush_timer = QTimer()
        self._sc_flush_timer.setInterval(100)
        self._sc_flush_timer.timeout.connect(self._sc_flush_pending_logs)
        self._sc_flush_timer.start()

        self._sc_load_persisted_state()

    # --- toolbar ---

    def _build_sc_toolbar(self):
        frame = QFrame()
        frame.setObjectName("scToolbar")
        frame.setFixedHeight(40)
        frame.setStyleSheet("""
            QFrame#scToolbar {
                background-color: #050b1e;
                border-bottom: 1px solid #1e293b;
            }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(4)

        self._sc_connect_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "connect.svg"), "Connect"
        )
        self._sc_connect_btn.setStyleSheet(f"""
            QPushButton {{
                min-height: 0px; max-height: 30px; padding: 4px 14px; border-radius: 6px;
                background-color: #07202b; color: #34d399; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 700; border: none;
            }}
            QPushButton:hover {{ background-color: #0a2d3b; }}
            QPushButton:pressed {{ background-color: #051820; }}
        """)
        icon_conn = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "connect.svg"), "#34d399", 13)
        if not icon_conn.isNull():
            self._sc_connect_btn.setIcon(icon_conn)
        layout.addWidget(self._sc_connect_btn)

        self._sc_pause_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "pause.svg"), "Pause"
        )
        self._sc_pause_btn.setCheckable(True)
        layout.addWidget(self._sc_pause_btn)

        self._sc_stop_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "stop.svg"), "Stop"
        )
        layout.addWidget(self._sc_stop_btn)

        self._sc_refresh_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "refresh.svg"), "Refresh"
        )
        layout.addWidget(self._sc_refresh_btn)

        self._sc_add_log_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "plus.svg"), ""
        )
        self._sc_add_log_btn.setFixedSize(28, 28)
        self._sc_add_log_btn.setToolTip("Add LOG panel")
        self._sc_add_log_btn.setStyleSheet("""
            QPushButton {
                min-height: 0px; max-height: 28px; min-width: 28px; max-width: 28px;
                padding: 0px; border-radius: 7px;
                background-color: transparent; color: #94a3b8; border: 1px solid #1e293b;
            }
            QPushButton:hover { border-color: #334155; }
            QPushButton:focus { border-color: #818CF8; background-color: #0f172a; }
            QPushButton:pressed { background-color: #050b1e; }
        """)
        icon_add = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "plus.svg"), "#34d399", 14)
        if not icon_add.isNull():
            self._sc_add_log_btn.setIcon(icon_add)
        layout.addWidget(self._sc_add_log_btn)

        self._sc_remove_log_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "minus.svg"), ""
        )
        self._sc_remove_log_btn.setFixedSize(28, 28)
        self._sc_remove_log_btn.setToolTip("Remove current LOG panel")
        self._sc_remove_log_btn.setStyleSheet("""
            QPushButton {
                min-height: 0px; max-height: 28px; min-width: 28px; max-width: 28px;
                padding: 0px; border-radius: 7px;
                background-color: transparent; color: #94a3b8; border: 1px solid #1e293b;
            }
            QPushButton:hover { border-color: #334155; }
            QPushButton:focus { border-color: #818CF8; background-color: #0f172a; }
            QPushButton:pressed { background-color: #050b1e; }
            QPushButton:disabled { background-color: transparent; border-color: #1e293b; }
        """)
        icon_remove = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "minus.svg"), "#f43f5e", 14)
        if not icon_remove.isNull():
            self._sc_remove_log_btn.setIcon(icon_remove)
        self._sc_remove_log_btn.setEnabled(False)
        layout.addWidget(self._sc_remove_log_btn)

        layout.addSpacing(6)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: #1e293b;")
        layout.addWidget(sep)

        layout.addSpacing(6)

        self._sc_sidebar_toggle_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "sidebar.svg"), "Sidebar"
        )
        self._sc_sidebar_toggle_btn.setCheckable(True)
        self._sc_sidebar_toggle_btn.setChecked(True)
        layout.addWidget(self._sc_sidebar_toggle_btn)

        layout.addStretch()

        self._sc_settings_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "settings.svg"), "Settings"
        )
        layout.addWidget(self._sc_settings_btn)

        return frame

    # --- sidebar ---

    def _build_sc_sidebar(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(self._sc_sidebar_min_width)
        scroll.setMaximumWidth(340)
        scroll.setStyleSheet("""
            QScrollArea { background-color: #050b1e; border: none; }
            QScrollArea > QWidget > QWidget { background-color: #050b1e; }
        """)

        vbar = scroll.verticalScrollBar()
        vbar.setFixedWidth(4)
        vbar.setStyleSheet("""
            QScrollBar:vertical {
                width: 4px;
                margin: 0px;
                background: transparent;
                border: none;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical {
                background: #1f315d;
                min-height: 24px;
                border-radius: 2px;
            }
            QScrollBar::handle:vertical:hover {
                background: #2a3a6a;
            }
            QScrollBar::sub-line:vertical,
            QScrollBar::add-line:vertical {
                height: 0px;
                width: 0px;
                background: transparent;
                border: none;
                subcontrol-origin: margin;
            }
            QScrollBar::up-arrow:vertical,
            QScrollBar::down-arrow:vertical {
                image: none;
                width: 0px;
                height: 0px;
                background: transparent;
                border: none;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(12)

        root.addWidget(self._build_sc_section_port_settings())
        root.addWidget(self._build_sc_section_rx_settings())
        root.addWidget(self._build_sc_section_tx_settings())
        root.addStretch()

        scroll.setWidget(container)
        return scroll

    def _build_sc_section_port_settings(self):
        grp = self._make_sc_section("Serial Config")
        layout = grp.property("_inner_layout")

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(10)

        grid.addWidget(self._make_sc_label("Port"), 0, 0)
        self._sc_port_combo = DarkComboBox()
        self._sc_port_combo.setFixedHeight(28)
        self._sc_port_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self._sc_port_combo.setMinimumWidth(60)
        f = self._sc_port_combo.font()
        f.setPixelSize(12)
        self._sc_port_combo.setFont(f)
        grid.addWidget(self._sc_port_combo, 0, 1)

        grid.addWidget(self._make_sc_label("Baudrate"), 1, 0)
        self._sc_baud_combo = DarkComboBox()
        self._sc_baud_combo.setFixedHeight(28)
        self._sc_baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000", "Custom"]:
            self._sc_baud_combo.addItem(br)
        self._sc_baud_combo.setCurrentIndex(0)
        f2 = self._sc_baud_combo.font()
        f2.setPixelSize(12)
        self._sc_baud_combo.setFont(f2)
        grid.addWidget(self._sc_baud_combo, 1, 1)

        self._sc_auto_detect_cb = QCheckBox("Auto-Detect")
        self._sc_auto_detect_cb.setChecked(True)
        self._sc_auto_detect_cb.setStyleSheet(self._sc_checkbox_style())
        grid.addWidget(self._sc_auto_detect_cb, 2, 1)
        self._sc_baud_combo.setEditable(False)
        self._sc_baud_combo.setEnabled(False)

        grid.addWidget(self._make_sc_label("Data bits"), 3, 0)
        self._sc_databit_combo = DarkComboBox()
        self._sc_databit_combo.setFixedHeight(28)
        for d in ["8", "7", "6", "5"]:
            self._sc_databit_combo.addItem(d)
        grid.addWidget(self._sc_databit_combo, 3, 1)

        grid.addWidget(self._make_sc_label("Flow Control"), 4, 0)
        self._sc_flow_combo = DarkComboBox()
        self._sc_flow_combo.setFixedHeight(28)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._sc_flow_combo.addItem(fc)
        grid.addWidget(self._sc_flow_combo, 4, 1)

        grid.addWidget(self._make_sc_label("Stop bits"), 5, 0)
        self._sc_stopbit_combo = DarkComboBox()
        self._sc_stopbit_combo.setFixedHeight(28)
        for s in ["1", "1.5", "2"]:
            self._sc_stopbit_combo.addItem(s)
        grid.addWidget(self._sc_stopbit_combo, 5, 1)

        grid.addWidget(self._make_sc_label("Parity"), 6, 0)
        self._sc_parity_combo = DarkComboBox()
        self._sc_parity_combo.setFixedHeight(28)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._sc_parity_combo.addItem(p)
        grid.addWidget(self._sc_parity_combo, 6, 1)

        layout.addLayout(grid)
        return grp

    _TOGGLE_W = 80
    _SPIN_W = _TOGGLE_W // 2
    _MS_LABEL_W = 16
    _COMBO_END_W = _SPIN_W + 4 + _MS_LABEL_W

    def _build_sc_section_rx_settings(self):
        grp = self._make_sc_section("RX Config")
        layout = grp.property("_inner_layout")

        row1 = QHBoxLayout()
        row1.setSpacing(4)
        row1.addWidget(self._make_sc_label("Format"))
        row1.addStretch()
        self._sc_rx_toggle = _MiniSlideToggle("ASCII", "HEX")
        self._sc_rx_toggle.toggled.connect(lambda v: setattr(self, '_sc_rx_display_hex', v == "HEX"))
        row1.addWidget(self._sc_rx_toggle)
        layout.addLayout(row1)

        row_af = QHBoxLayout()
        row_af.setSpacing(4)
        self._sc_rx_auto_flush_cb = QCheckBox("Auto Flush")
        self._sc_rx_auto_flush_cb.setToolTip("Flush RX data to the log after the configured idle interval")
        self._sc_rx_auto_flush_cb.setStyleSheet(self._sc_checkbox_style())
        row_af.addWidget(self._sc_rx_auto_flush_cb)
        row_af.addStretch()
        self._sc_rx_auto_flush_spin = QSpinBox()
        self._sc_rx_auto_flush_spin.setRange(10, 60000)
        self._sc_rx_auto_flush_spin.setValue(50)
        self._sc_rx_auto_flush_spin.setSingleStep(10)
        self._sc_rx_auto_flush_spin.setFixedSize(self._SPIN_W, 24)
        self._sc_rx_auto_flush_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: #020618; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
                color: #cbd5e1; font-size: 12px; font-family: {_UI_FONT}; padding: 1px 2px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: 10px; }}
        """)
        row_af.addWidget(self._sc_rx_auto_flush_spin)
        af_unit = QLabel("ms")
        af_unit.setFixedWidth(self._MS_LABEL_W)
        af_unit.setStyleSheet(f"color: #94a3b8; font-size: 11px; font-family: {_TERM_FONT}; background: transparent; border: none;")
        row_af.addWidget(af_unit)
        layout.addLayout(row_af)

        self._sc_rx_show_time_cb = QCheckBox("Show Time (ms)")
        self._sc_rx_show_time_cb.setChecked(True)
        self._sc_rx_show_time_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_rx_show_time_cb.toggled.connect(lambda v: setattr(self, '_sc_show_timestamp', v))
        layout.addWidget(self._sc_rx_show_time_cb)

        return grp

    def _build_sc_section_tx_settings(self):
        grp = self._make_sc_section("TX Config")
        layout = grp.property("_inner_layout")

        row1 = QHBoxLayout()
        row1.setSpacing(4)
        row1.addWidget(self._make_sc_label("Format"))
        row1.addStretch()
        self._sc_tx_toggle = _MiniSlideToggle("ASCII", "HEX")
        self._sc_tx_toggle.toggled.connect(lambda v: setattr(self, '_sc_tx_display_hex', v == "HEX"))
        row1.addWidget(self._sc_tx_toggle)
        layout.addLayout(row1)

        row_auto = QHBoxLayout()
        row_auto.setSpacing(4)
        self._sc_auto_resend_cb = QCheckBox("Auto Send")
        self._sc_auto_resend_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_auto_resend_cb.toggled.connect(self._sc_on_auto_resend_toggled)
        row_auto.addWidget(self._sc_auto_resend_cb)
        row_auto.addStretch()
        self._sc_resend_spin = QSpinBox()
        self._sc_resend_spin.setRange(100, 60000)
        self._sc_resend_spin.setValue(1000)
        self._sc_resend_spin.setSingleStep(100)
        self._sc_resend_spin.setFixedSize(self._SPIN_W, 24)
        self._sc_resend_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: #020618; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
                color: #cbd5e1; font-size: 12px; font-family: {_UI_FONT}; padding: 1px 2px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: 10px; }}
        """)
        row_auto.addWidget(self._sc_resend_spin)
        auto_unit = QLabel("ms")
        auto_unit.setFixedWidth(self._MS_LABEL_W)
        auto_unit.setStyleSheet(f"color: #94a3b8; font-size: 11px; font-family: {_TERM_FONT}; background: transparent; border: none;")
        row_auto.addWidget(auto_unit)
        layout.addLayout(row_auto)

        row_ending = QHBoxLayout()
        row_ending.setSpacing(4)
        row_ending.addWidget(self._make_sc_label("Line Ending"))
        row_ending.addStretch()
        self._sc_ending_combo = DarkComboBox()
        self._sc_ending_combo.setFixedHeight(26)
        self._sc_ending_combo.setFixedWidth(self._COMBO_END_W)
        for label, val in [("\\r\\n", "\r\n"), ("\\n", "\n"), ("\\r", "\r"), ("\\n\\r", "\n\r"), ("None", "")]:
            self._sc_ending_combo.addItem(label, val)
        self._sc_ending_combo.setCurrentIndex(0)
        f = self._sc_ending_combo.font()
        f.setPixelSize(12)
        self._sc_ending_combo.setFont(f)
        self._sc_ending_combo.currentIndexChanged.connect(
            lambda i: setattr(self, '_sc_line_ending', self._sc_ending_combo.itemData(i) or "")
        )
        row_ending.addWidget(self._sc_ending_combo)
        layout.addLayout(row_ending)

        self._sc_show_send_cb = QCheckBox("Show Sent Data")
        self._sc_show_send_cb.setChecked(True)
        self._sc_show_send_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_show_send_cb.toggled.connect(lambda v: setattr(self, '_sc_show_send', v))
        layout.addWidget(self._sc_show_send_cb)

        self._sc_line_by_line_cb = QCheckBox("Line by Line")
        self._sc_line_by_line_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_line_by_line_cb.toggled.connect(lambda v: setattr(self, '_sc_line_by_line', v))
        layout.addWidget(self._sc_line_by_line_cb)

        return grp

    # --- log area ---

    def _build_sc_log_area(self):
        frame = QFrame()
        frame.setObjectName("scLogFrame")
        frame.setStyleSheet("""
            QFrame#scLogFrame {
                background-color: #020618;
                border: none;
                border-radius: 0px;
            }
        """)
        frame.setProperty("_is_primary", True)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(6, 4, 6, 2)
        toolbar.setSpacing(4)

        icon_label = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "logs.svg"), "#cbd5e1", 12)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(12, 12))
        icon_label.setFixedSize(14, 14)
        icon_label.setStyleSheet("background: transparent;")
        toolbar.addWidget(icon_label)

        title = QLabel("Serial Log")
        title.setStyleSheet(f"color: #FFFFFF; font-size: 14px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;")
        toolbar.addWidget(title)

        toolbar.addStretch()

        self._sc_filter_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "filter.svg"), "Filter", tone="log"
        )
        self._sc_filter_btn.setCheckable(True)
        toolbar.addWidget(self._sc_filter_btn)

        self._sc_copy_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "copy.svg"), "Copy", tone="log"
        )
        toolbar.addWidget(self._sc_copy_btn)

        self._sc_export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export", tone="log"
        )
        toolbar.addWidget(self._sc_export_btn)

        self._sc_clear_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), "Clear", tone="log"
        )
        toolbar.addWidget(self._sc_clear_btn)

        self._sc_scroll_lock_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"), "Auto-scroll", tone="log"
        )
        self._sc_scroll_lock_btn.setCheckable(True)
        self._sc_scroll_lock_btn.setChecked(True)
        self._sc_scroll_lock_btn.setStyleSheet(f"""
            QPushButton {{
                min-height: 0px; max-height: 28px; padding: 5px 11px; border-radius: 7px;
                background-color: rgba(15, 23, 42, 0.6); color: #cbd5e1; font-size: 12px;
                font-family: {_UI_FONT}; font-weight: 500; border: 1px solid #334155;
            }}
            QPushButton:hover {{ background-color: #1e293b; color: #FFFFFF; border: 1px solid #475569; }}
            QPushButton:focus {{ background-color: #1e293b; color: #FFFFFF; border: 1px solid #818CF8; }}
            QPushButton:pressed {{ background-color: #0f172a; }}
            QPushButton:checked {{
                background-color: #0c4a3e; color: #5eead4; border: 1px solid #2dd4bf;
                font-weight: 600;
            }}
            QPushButton:checked:hover {{
                background-color: #115e50; color: #99f6e4; border: 1px solid #5eead4;
            }}
        """)
        toolbar.addWidget(self._sc_scroll_lock_btn)

        layout.addLayout(toolbar)

        self._sc_filter_row = QWidget()
        self._sc_filter_row.setVisible(False)
        self._sc_filter_row.setStyleSheet("background: transparent;")
        filter_root = QVBoxLayout(self._sc_filter_row)
        filter_root.setContentsMargins(6, 0, 6, 2)
        filter_root.setSpacing(3)

        fl = QHBoxLayout()
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(4)
        self._sc_filter_input = QLineEdit()
        self._sc_filter_input.setPlaceholderText("Enter keyword or regex, press Enter to filter...")
        self._sc_filter_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
                color: {_CLR_INPUT_TEXT}; font-size: 12px; font-family: {_UI_FONT}; padding: 3px 7px; min-height: 24px; max-height: 24px;
                selection-background-color: {_CLR_SELECTION_BG}; selection-color: {_CLR_SELECTION_TEXT};
            }}
            QLineEdit:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
        """)
        fl.addWidget(self._sc_filter_input, 1)

        self._sc_filter_match_label = QLabel("")
        self._sc_filter_match_label.setStyleSheet(
            f"color: {_CLR_FILTER_TEXT}; font-size: 11px; font-family: {_UI_FONT}; background: transparent; min-width: 60px;"
        )
        fl.addWidget(self._sc_filter_match_label)
        filter_root.addLayout(fl)

        opts = QHBoxLayout()
        opts.setContentsMargins(0, 0, 0, 0)
        opts.setSpacing(8)

        self._sc_filter_regex_cb = QCheckBox("Regex")
        self._sc_filter_regex_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_filter_regex_cb.setToolTip("Enable regex matching")
        opts.addWidget(self._sc_filter_regex_cb)

        self._sc_filter_case_cb = QCheckBox("Match Case")
        self._sc_filter_case_cb.setStyleSheet(self._sc_checkbox_style())
        opts.addWidget(self._sc_filter_case_cb)

        self._sc_filter_invert_cb = QCheckBox("Invert")
        self._sc_filter_invert_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_filter_invert_cb.setToolTip("Show non-matching lines")
        opts.addWidget(self._sc_filter_invert_cb)

        opts.addSpacing(8)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setFixedHeight(14)
        sep.setStyleSheet("color: #1e293b; background: transparent;")
        opts.addWidget(sep)

        opts.addSpacing(4)

        before_lbl = QLabel("Before")
        before_lbl.setStyleSheet(f"color: #94a3b8; font-size: 12px; font-family: {_UI_FONT}; background: transparent;")
        opts.addWidget(before_lbl)
        self._sc_filter_before_spin = QSpinBox()
        self._sc_filter_before_spin.setRange(0, 999)
        self._sc_filter_before_spin.setValue(0)
        self._sc_filter_before_spin.setFixedSize(56, 24)
        self._sc_filter_before_spin.setToolTip("Show N lines before matched lines")
        self._sc_filter_before_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: #020618; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
                color: #cbd5e1; font-size: 12px; font-family: {_UI_FONT}; padding: 0px 2px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: 10px; }}
        """)
        opts.addWidget(self._sc_filter_before_spin)
        before_unit = QLabel("lines")
        before_unit.setStyleSheet(f"color: #94a3b8; font-size: 11px; font-family: {_UI_FONT}; background: transparent;")
        opts.addWidget(before_unit)

        opts.addSpacing(4)

        after_lbl = QLabel("After")
        after_lbl.setStyleSheet(f"color: #94a3b8; font-size: 12px; font-family: {_UI_FONT}; background: transparent;")
        opts.addWidget(after_lbl)
        self._sc_filter_after_spin = QSpinBox()
        self._sc_filter_after_spin.setRange(0, 999)
        self._sc_filter_after_spin.setValue(0)
        self._sc_filter_after_spin.setFixedSize(56, 24)
        self._sc_filter_after_spin.setToolTip("Show N lines after matched lines")
        self._sc_filter_after_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: #020618; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
                color: #cbd5e1; font-size: 12px; font-family: {_UI_FONT}; padding: 0px 2px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{ width: 10px; }}
        """)
        opts.addWidget(self._sc_filter_after_spin)
        after_unit = QLabel("lines")
        after_unit.setStyleSheet(f"color: #94a3b8; font-size: 11px; font-family: {_UI_FONT}; background: transparent;")
        opts.addWidget(after_unit)

        opts.addStretch()
        filter_root.addLayout(opts)

        layout.addWidget(self._sc_filter_row)

        self._sc_log_edit = QTextEdit()
        self._sc_log_edit.setReadOnly(True)
        self._sc_log_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {_CLR_BG_LOG}; border: none; border-top: 1px solid {_CLR_BORDER};
                color: {_CLR_TEXT_BODY}; font-family: {_TERM_FONT}; font-size: 14px; font-weight: 400;
                padding: 6px 8px;
                selection-background-color: {_CLR_SELECTION_BG};
                selection-color: {_CLR_SELECTION_TEXT};
            }}
        """ + SCROLLBAR_STYLE)
        self._sc_log_edit.document().setDefaultStyleSheet(
            "p, div { line-height: 150%; margin: 0; padding: 0; }"
        )
        self._sc_log_edit.document().setMaximumBlockCount(5000)
        layout.addWidget(self._sc_log_edit, 1)

        if self._sc_log_edit.verticalScrollBar():
            self._sc_log_edit.verticalScrollBar().valueChanged.connect(self._sc_on_user_scroll)

        self._sc_status_bar = self._build_sc_status_bar()
        layout.addWidget(self._sc_status_bar)

        return frame

    # --- send area ---

    def _build_sc_send_area(self):
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        send_row = QHBoxLayout()
        send_row.setSpacing(3)

        self._sc_history_combo = DarkComboBox()
        self._sc_history_combo.setEditable(True)
        self._sc_history_combo.setInsertPolicy(DarkComboBox.NoInsert)
        self._sc_history_combo.setFixedHeight(30)
        self._sc_send_input = self._sc_history_combo.lineEdit()
        self._sc_send_input.setPlaceholderText("Enter text to send (\u2193 for history)...")
        self._sc_send_input.setClearButtonEnabled(False)
        self._sc_history_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {_CLR_INPUT_BG}; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
                color: {_CLR_INPUT_TEXT}; font-size: 14px; font-family: {_UI_FONT};
                padding: 3px 28px 3px 8px;
                selection-background-color: {_CLR_SELECTION_BG};
                selection-color: {_CLR_SELECTION_TEXT};
            }}
            QComboBox:focus {{ border: 1px solid {_CLR_BORDER_HOVER}; }}
            QComboBox::drop-down {{ border: none; width: 22px; }}
            QComboBox::down-arrow {{ image: none; width: 0px; height: 0px; }}
            QComboBox QLineEdit {{
                background-color: transparent; border: none;
                color: {_CLR_INPUT_TEXT}; font-size: 14px; font-family: {_UI_FONT};
                padding: 0px; margin: 0px;
                selection-background-color: {_CLR_SELECTION_BG};
                selection-color: {_CLR_SELECTION_TEXT};
            }}
        """)
        send_row.addWidget(self._sc_history_combo, 1)

        self._sc_send_btn = QPushButton("Send")
        self._sc_send_btn.setCursor(Qt.PointingHandCursor)
        self._sc_send_btn.setFixedHeight(30)
        icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "send.svg"), _CLR_BG_MAIN, 11)
        if not icon.isNull():
            self._sc_send_btn.setIcon(icon)
        self._sc_send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_CLR_SEND_BG}; border: none; border-radius: 6px;
                color: {_CLR_BG_MAIN}; font-weight: 700; font-size: 14px;
                font-family: {_UI_FONT}; padding: 3px 18px;
            }}
            QPushButton:hover {{ background-color: {_CLR_SEND_HOVER}; }}
            QPushButton:pressed {{ background-color: {_CLR_SEND_PRESS}; }}
        """)
        send_row.addWidget(self._sc_send_btn)

        layout.addLayout(send_row)

        return widget

    # --- quick commands ---

    def _build_sc_quick_commands(self):
        frame = QFrame()
        # 双 objectName 不可行：保留 scQuickFrame 给现有内嵌 QSS；面板级 QSS 通过 quickCommandsPanel 选择器命中
        frame.setObjectName("quickCommandsPanel")
        frame.setProperty("class", "scQuickFrame")
        # 外层面板 + 内部分隔条：背景柔和、低对比边框、圆角；不改变布局
        frame.setStyleSheet(f"""
            QFrame#quickCommandsPanel {{
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 6px;
            }}
            QFrame#scQuickHeaderFrame {{
                background: transparent;
                border: none;
                border-bottom: 1px solid #1e293b;
            }}
            QFrame#scQuickToolbar {{
                background: transparent;
                border: none;
                border-bottom: 1px solid #1e293b;
            }}
            /* 标题强调色 */
            QLabel#quickCommandsTitle {{
                color: #fbbf24;
                font-weight: 600;
                font-size: 13px;
                font-family: {_UI_FONT};
                background: transparent;
            }}
            /* 普通操作按钮（+ Group / Import / Export 等通过 _make_sc_btn 的 QPushButton） */
            QFrame#quickCommandsPanel QPushButton {{
                background-color: #1e293b;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 12px;
                min-height: 24px;
            }}
            QFrame#quickCommandsPanel QPushButton:hover {{
                background-color: #334155;
                border-color: #475569;
                color: #ffffff;
            }}
            QFrame#quickCommandsPanel QPushButton:pressed {{
                background-color: #475569;
                border-color: #64748b;
            }}
            QFrame#quickCommandsPanel QPushButton:disabled {{
                background-color: #111827;
                color: #64748b;
                border-color: #1e293b;
            }}
            /* 主操作按钮：+ Add */
            QFrame#quickCommandsPanel QPushButton#primaryButton {{
                background-color: #1d4ed8;
                color: #ffffff;
                border: 1px solid #3b82f6;
            }}
            QFrame#quickCommandsPanel QPushButton#primaryButton:hover {{
                background-color: #2563eb;
                border-color: #60a5fa;
            }}
            QFrame#quickCommandsPanel QPushButton#primaryButton:pressed {{
                background-color: #1e40af;
            }}
            /* 快捷指令按钮 */
            QFrame#quickCommandsPanel QPushButton#quickCommandButton {{
                background-color: #172033;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 5px 12px;
                min-height: 24px;
                min-width: 48px;
            }}
            QFrame#quickCommandsPanel QPushButton#quickCommandButton:hover {{
                background-color: #25344d;
                border-color: #3b82f6;
                color: #ffffff;
            }}
            QFrame#quickCommandsPanel QPushButton#quickCommandButton:pressed {{
                background-color: #1d4ed8;
                border-color: #60a5fa;
            }}
            /* QScrollArea 透明背景 */
            QFrame#quickCommandsPanel QScrollArea {{
                background: transparent;
                border: none;
            }}
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- header: 标题 + 项目 Tab 栏 ---
        header_frame = QFrame()
        header_frame.setObjectName("scQuickHeaderFrame")
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(8, 6, 8, 0)
        header.setSpacing(6)

        zap_icon = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "zap.svg"), "#f59e0b", 11)
        if not icon.isNull():
            zap_icon.setPixmap(icon.pixmap(11, 11))
        zap_icon.setFixedSize(13, 13)
        zap_icon.setStyleSheet("background: transparent;")
        header.addWidget(zap_icon)

        lbl = QLabel("Quick Commands")
        lbl.setObjectName("quickCommandsTitle")
        # 颜色 / 字号由面板级 QSS (#quickCommandsTitle) 接管，此处仅设置背景透明以避免被父容器覆盖
        lbl.setStyleSheet("background: transparent;")
        header.addWidget(lbl)

        # 项目 Tab 栏（最顶层分组），末尾内置 "+" 加号 tab，右键菜单 + 拖拽排序
        self._sc_qc_project_tabs = _ProjectTabBar()
        self._sc_qc_project_tabs.setExpanding(False)
        self._sc_qc_project_tabs.setDrawBase(False)
        self._sc_qc_project_tabs.setUsesScrollButtons(True)
        self._sc_qc_project_tabs.setStyleSheet(f"""
            QTabBar {{
                background: transparent;
                border-bottom: 1px solid #1e293b;
            }}
            QTabBar::tab {{
                background-color: #0f172a;
                color: #cbd5e1;
                border: 1px solid #475569;
                border-top: 2px solid #475569;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 4px 14px;
                margin-right: 2px;
                margin-bottom: 0px;
                min-height: 22px;
                font-size: 12px;
                font-family: {_UI_FONT};
            }}
            QTabBar::tab:hover {{
                background-color: #1e293b;
                color: #f1f5f9;
                border-color: #64748b;
                border-top-color: #64748b;
            }}
            QTabBar::tab:selected {{
                background-color: #0f172a;
                color: #f8fafc;
                border: 1px solid #475569;
                border-top: 2px solid #3b82f6;
                border-bottom: none;
            }}
            QTabBar::tab:selected:hover {{
                background-color: #0f172a;
                color: #ffffff;
            }}
            QTabBar::tab:!selected {{
                margin-top: 0px;
            }}
            QTabBar::tear {{
                background: transparent;
                border: none;
                width: 0px;
            }}
            QTabBar QToolButton {{
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 3px;
                color: #94a3b8;
                margin: 2px;
            }}
            QTabBar QToolButton:hover {{
                background-color: #1e293b;
                border-color: #475569;
                color: #e2e8f0;
            }}
        """)
        header.addWidget(self._sc_qc_project_tabs, 1)

        layout.addWidget(header_frame)

        # --- 工具栏:区域/分组下拉 + 操作按钮 ---
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("scQuickToolbar")
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setContentsMargins(8, 6, 8, 6)
        toolbar.setSpacing(6)

        _combo_qss = f"""
            QComboBox {{
                background-color: #0b1220;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 3px 8px;
                min-height: 24px;
                font-size: 12px;
                font-family: {_UI_FONT};
                min-width: 90px;
            }}
            QComboBox:hover {{ border-color: #475569; }}
            QComboBox:focus {{ border-color: #3b82f6; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{
                background-color: #0f172a;
                color: #e5e7eb;
                border: 1px solid #334155;
                selection-background-color: #2563eb;
                selection-color: #ffffff;
                outline: 0;
            }}
        """

        group_lbl = QLabel("Group:")
        group_lbl.setStyleSheet(
            f"color: #cbd5e1; font-size: 12px; font-family: {_UI_FONT}; background: transparent;"
        )
        toolbar.addWidget(group_lbl)
        self._sc_qc_group_combo = QComboBox()
        self._sc_qc_group_combo.setStyleSheet(_combo_qss)
        self._sc_qc_group_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        toolbar.addWidget(self._sc_qc_group_combo)

        self._sc_qc_new_group_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "plus.svg"), "Group", tone="quick"
        )
        # 工具栏统一暗色按钮样式：覆盖 _make_sc_btn(quick) 的局部 setStyleSheet
        _toolbar_btn_qss = f"""
            QPushButton {{
                background-color: #1e293b;
                color: #e5e7eb;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 12px;
                min-height: 24px;
                font-size: 12px;
                font-family: {_UI_FONT};
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #334155;
                border-color: #475569;
                color: #ffffff;
            }}
            QPushButton:pressed {{
                background-color: #475569;
                border-color: #64748b;
            }}
            QPushButton:disabled {{
                background-color: #111827;
                color: #64748b;
                border-color: #1e293b;
            }}
        """
        self._sc_qc_new_group_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_qc_new_group_btn)

        toolbar.addStretch()

        self._sc_qc_add_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "plus.svg"), "Add", tone="quick"
        )
        # + Add 作为主操作按钮：蓝色突出
        self._sc_qc_add_btn.setObjectName("primaryButton")
        self._sc_qc_add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #1d4ed8;
                color: #ffffff;
                border: 1px solid #3b82f6;
                border-radius: 6px;
                padding: 4px 12px;
                min-height: 24px;
                font-size: 12px;
                font-family: {_UI_FONT};
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #2563eb;
                border-color: #60a5fa;
            }}
            QPushButton:pressed {{
                background-color: #1e40af;
                border-color: #3b82f6;
            }}
        """)
        toolbar.addWidget(self._sc_qc_add_btn)

        self._sc_qc_import_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "import.svg"), "Import", tone="quick"
        )
        self._sc_qc_import_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_qc_import_btn)

        self._sc_qc_export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export", tone="quick"
        )
        self._sc_qc_export_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_qc_export_btn)

        layout.addWidget(toolbar_frame)

        # --- 按钮区:QScrollArea + QGridLayout ---
        self._sc_qc_btn_scroll = QScrollArea()
        self._sc_qc_btn_scroll.setWidgetResizable(True)
        self._sc_qc_btn_scroll.setFrameShape(QFrame.NoFrame)
        self._sc_qc_btn_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            f"{SCROLLBAR_STYLE}"
        )
        self._sc_qc_btn_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._sc_qc_btn_scroll.setMinimumHeight(56)
        self._sc_qc_btn_scroll.setMaximumHeight(140)

        self._sc_qc_btn_container = QWidget()
        self._sc_qc_btn_container.setObjectName("scQuickBtnContainer")
        self._sc_qc_btn_container.setStyleSheet(
            "QWidget#scQuickBtnContainer { background: transparent; }"
        )
        # 接受拖拽：本控件作为快捷指令按钮的统一 drop 目标，事件经 eventFilter 派发
        self._sc_qc_btn_container.setAcceptDrops(True)
        self._sc_qc_btn_container.installEventFilter(self)
        self._sc_qc_btn_layout = QGridLayout(self._sc_qc_btn_container)
        self._sc_qc_btn_layout.setContentsMargins(8, 6, 8, 8)
        self._sc_qc_btn_layout.setHorizontalSpacing(6)
        self._sc_qc_btn_layout.setVerticalSpacing(6)

        self._sc_qc_btn_scroll.setWidget(self._sc_qc_btn_container)
        layout.addWidget(self._sc_qc_btn_scroll)

        return frame

    # --- status bar ---

    def _build_sc_status_bar(self):
        frame = QFrame()
        frame.setObjectName("scStatusBar")
        frame.setFixedHeight(28)
        frame.setStyleSheet(f"""
            QFrame#scStatusBar {{
                background-color: #050b1e;
                border-top: 1px solid #1e293b;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QLabel {{ font-size: 11px; font-family: {_TERM_FONT}; background: transparent; }}
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(10, 2, 10, 2)
        layout.setSpacing(14)

        self._sc_status_port_label = QLabel("\u2022 Port: Unconnected")
        self._sc_status_port_label.setStyleSheet("color: #f43f5e;")
        layout.addWidget(self._sc_status_port_label)

        self._sc_status_baud_label = QLabel("Baud rate: -")
        self._sc_status_baud_label.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self._sc_status_baud_label)

        self._sc_status_rx_label = QLabel("RX: 0 B")
        self._sc_status_rx_label.setStyleSheet(f"color: {_CLR_RX};")
        layout.addWidget(self._sc_status_rx_label)

        self._sc_status_tx_label = QLabel("TX: 0 B")
        self._sc_status_tx_label.setStyleSheet(f"color: {_CLR_TX};")
        layout.addWidget(self._sc_status_tx_label)

        self._sc_status_autobaud_label = QLabel("")
        self._sc_status_autobaud_label.setStyleSheet("color: #818CF8;")
        self._sc_status_autobaud_label.setVisible(False)
        layout.addWidget(self._sc_status_autobaud_label)

        layout.addStretch()

        return frame

    # --- signal binding ---

    def _bind_sc_signals(self):
        self._sc_connect_btn.clicked.connect(self._sc_on_connect_toggle)
        self._sc_pause_btn.clicked.connect(self._sc_on_pause)
        self._sc_stop_btn.clicked.connect(self._sc_on_stop)
        self._sc_refresh_btn.clicked.connect(self._sc_on_refresh)
        self._sc_add_log_btn.clicked.connect(self._sc_on_add_log_panel)
        self._sc_remove_log_btn.clicked.connect(self._sc_on_remove_log_panel)
        self._sc_sidebar_toggle_btn.clicked.connect(self._sc_on_sidebar_toggle)
        self._sc_settings_btn.clicked.connect(self._sc_open_settings_dialog)

        self._sc_filter_btn.clicked.connect(self._sc_on_filter_toggle)
        self._sc_filter_input.returnPressed.connect(self._sc_apply_filter)
        self._sc_filter_input.textChanged.connect(self._sc_on_filter_input_changed)
        self._sc_filter_regex_cb.toggled.connect(self._sc_on_filter_option_changed)
        self._sc_filter_case_cb.toggled.connect(self._sc_on_filter_option_changed)
        self._sc_filter_invert_cb.toggled.connect(self._sc_on_filter_option_changed)
        self._sc_filter_before_spin.valueChanged.connect(self._sc_on_filter_option_changed)
        self._sc_filter_after_spin.valueChanged.connect(self._sc_on_filter_option_changed)
        self._sc_copy_btn.clicked.connect(self._sc_copy_logs)
        self._sc_export_btn.clicked.connect(self._sc_export_logs)
        self._sc_clear_btn.clicked.connect(self._sc_clear_logs)
        self._sc_scroll_lock_btn.clicked.connect(
            lambda c: setattr(self, '_sc_auto_scroll', c)
        )

        self._sc_send_btn.clicked.connect(self._sc_on_send)
        self._sc_send_input.returnPressed.connect(self._sc_on_send)

        self._sc_qc_add_btn.clicked.connect(self._sc_add_quick_cmd)
        self._sc_qc_import_btn.clicked.connect(self._sc_import_quick_cmds)
        self._sc_qc_export_btn.clicked.connect(self._sc_export_quick_cmds)
        self._sc_qc_new_group_btn.clicked.connect(self._sc_qc_add_group)
        self._sc_qc_project_tabs.currentChanged.connect(self._sc_qc_on_project_tab_changed)
        self._sc_qc_project_tabs.customContextMenuRequested.connect(
            self._sc_qc_on_project_tab_context_menu
        )
        self._sc_qc_project_tabs.project_reorder_requested.connect(
            self._sc_qc_on_project_reorder
        )
        self._sc_qc_group_combo.currentIndexChanged.connect(self._sc_qc_on_group_changed)
        self._sc_qc_group_combo.customContextMenuRequested.connect(
            self._sc_qc_on_group_combo_context_menu
        )

        self._sc_baud_combo.activated.connect(lambda _idx: self._sc_on_baudrate_changed())
        _baud_line_edit = self._sc_baud_combo.lineEdit()
        if _baud_line_edit is not None:
            _baud_line_edit.editingFinished.connect(self._sc_on_baudrate_changed)

        self.serial_data_received.connect(self._sc_on_data_received)

        self._sc_auto_detect_cb.toggled.connect(self._sc_on_auto_detect_toggled)

        self._sc_rx_flush_timer = QTimer(self)
        self._sc_rx_flush_timer.setSingleShot(True)
        self._sc_rx_flush_timer.timeout.connect(self._sc_flush_rx_line_buf)

        self._sc_install_filter_shortcut()

    def _sc_install_filter_shortcut(self):
        host_widgets = []
        if getattr(self, "_sc_log_area", None) is not None:
            host_widgets.append(self._sc_log_area)
        if getattr(self, "_sc_send_input", None) is not None:
            host_widgets.append(self._sc_send_input)

        self._sc_filter_shortcuts = []
        for host in host_widgets:
            sc = QShortcut(QKeySequence("Ctrl+F"), host)
            sc.setContext(Qt.WidgetWithChildrenShortcut)
            sc.activated.connect(self._sc_toggle_filter_shortcut)
            self._sc_filter_shortcuts.append(sc)

    def _sc_toggle_filter_shortcut(self):
        btn = getattr(self, "_sc_filter_btn", None)
        if btn is None:
            return
        btn.click()
        if btn.isChecked():
            input_widget = getattr(self, "_sc_filter_input", None)
            if input_widget is not None:
                input_widget.setFocus(Qt.ShortcutFocusReason)
                input_widget.selectAll()

    # --- action handlers ---

    def _sc_on_connect_toggle(self):
        if self._serial_connected:
            self._sc_do_disconnect()
        else:
            self._sc_do_connect()

    def _sc_do_connect(self):
        port_text = self._sc_port_combo.currentText()
        if not port_text or port_text.startswith("No "):
            self._sc_append_system("[ERROR] No valid port selected")
            return

        port = port_text.split()[0]

        baud_text = self._sc_baud_combo.currentText().strip()
        try:
            baudrate = int(baud_text)
        except ValueError:
            self._sc_append_system(f"[ERROR] Invalid baud rate: {baud_text}")
            return

        databit = int(self._sc_databit_combo.currentText())
        stopbit_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}
        stopbits = stopbit_map.get(self._sc_stopbit_combo.currentText(), serial.STOPBITS_ONE)
        parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD,
                       "Mark": serial.PARITY_MARK, "Space": serial.PARITY_SPACE}
        parity = parity_map.get(self._sc_parity_combo.currentText(), serial.PARITY_NONE)
        flow = self._sc_flow_combo.currentText()
        xonxoff = flow == "XON/XOFF"
        rtscts = flow == "RTS/CTS"

        if DEBUG_MOCK:
            self._serial_conn = None
            self._serial_port = "MOCK"
            self._serial_baudrate = baudrate
            self._serial_connected = True
            self._sc_update_connect_ui(True)
            self._sc_append_system(f"[INFO] Mock connected: {port} @ {baudrate}")
            self.serial_connection_changed.emit(True)
            return

        try:
            conn = serial.Serial(
                port=port, baudrate=baudrate, bytesize=databit,
                stopbits=stopbits, parity=parity, xonxoff=xonxoff,
                rtscts=rtscts, timeout=0.1,
            )
            self._serial_conn = conn
            self._serial_port = port
            self._serial_baudrate = baudrate
            self._serial_connected = True
            self._sc_update_connect_ui(True)
            self._sc_append_system(f"[INFO] Connected: {port} @ {baudrate}")
            self.serial_connection_changed.emit(True)
            if self._sc_auto_detect_cb.isChecked():
                self._sc_auto_baud_monitor.enabled = True
                self._sc_auto_baud_monitor.runtime_redetect_enabled = True
                self._sc_auto_baud_pending_first_rx = True
                self._sc_auto_baud_initial_buf = bytearray()
                self._sc_auto_baud_initial_ts = time.perf_counter()
                self._sc_append_system("[INFO] Auto-detect enabled, waiting for RX data...")
            self._start_serial_read()
        except Exception as e:
            self._sc_append_system(f"[ERROR] Connection failed: {e}")

    def _sc_do_disconnect(self):
        self._stop_serial_read()
        self._sc_stop_auto_baud_scan()
        try:
            if self._serial_conn and self._serial_conn.is_open:
                self._serial_conn.close()
        except Exception as e:
            self._sc_append_system(f"[WARN] Close error: {e}")
        self._serial_conn = None
        self._serial_port = None
        self._serial_connected = False
        self._sc_update_connect_ui(False)
        self._sc_append_system("[INFO] Disconnected")
        self.serial_connection_changed.emit(False)

    def _sc_update_connect_ui(self, connected):
        if not hasattr(self, '_sc_connect_btn_fixed_width_applied'):
            self._sc_connect_btn.setFixedWidth(96)
            self._sc_connect_btn_fixed_width_applied = True
        if connected:
            self._sc_connect_btn.setText("Disconnect")
            self._sc_connect_btn.setStyleSheet(f"""
                QPushButton {{
                    min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                    background-color: #2b0a12; color: #f43f5e; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 700; border: none;
                }}
                QPushButton:hover {{ background-color: #3a0f18; }}
                QPushButton:focus {{ border: 1px solid #818CF8; }}
                QPushButton:pressed {{ background-color: #1c050a; }}
            """)
            icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "disconnect.svg"), "#f43f5e", 12)
            if not icon.isNull():
                self._sc_connect_btn.setIcon(icon)
            self._sc_status_port_label.setText(f"\u2022 Port: {self._serial_port}")
            self._sc_status_port_label.setStyleSheet(f"color: #34d399; font-size: 11px; font-family: {_TERM_FONT}; background: transparent;")
            baud = getattr(self, '_serial_baudrate', '-')
            self._sc_status_baud_label.setText(f"Baud rate: {baud}")
        else:
            self._sc_connect_btn.setText("Connect")
            self._sc_connect_btn.setStyleSheet(f"""
                QPushButton {{
                    min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                    background-color: #07202b; color: #34d399; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 700; border: none;
                }}
                QPushButton:hover {{ background-color: #0a2d3b; }}
                QPushButton:focus {{ border: 1px solid #818CF8; }}
                QPushButton:pressed {{ background-color: #051820; }}
            """)
            icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "connect.svg"), "#34d399", 12)
            if not icon.isNull():
                self._sc_connect_btn.setIcon(icon)
            self._sc_status_port_label.setText("\u2022 Port: Unconnected")
            self._sc_status_port_label.setStyleSheet(f"color: #f43f5e; font-size: 11px; font-family: {_TERM_FONT}; background: transparent;")
            self._sc_status_baud_label.setText("Baud rate: -")

        self._sc_port_combo.setEnabled(not connected)
        auto_detect_on = getattr(self, '_sc_auto_detect_cb', None) and self._sc_auto_detect_cb.isChecked()
        self._sc_baud_combo.setEditable(not auto_detect_on)
        self._sc_baud_combo.setEnabled(not auto_detect_on)

    def _sc_on_baudrate_changed(self):
        baud_text = self._sc_baud_combo.currentText().strip()
        try:
            baudrate = int(baud_text)
        except ValueError:
            if self._serial_connected:
                self._sc_append_system(f"[ERROR] Invalid baud rate: {baud_text}")
            return

        if baudrate == getattr(self, '_serial_baudrate', None):
            return

        if not self._serial_connected:
            self._serial_baudrate = baudrate
            return

        if DEBUG_MOCK or self._serial_conn is None:
            self._serial_baudrate = baudrate
            if hasattr(self, '_sc_status_baud_label'):
                self._sc_status_baud_label.setText(f"Baud rate: {baudrate}")
            self._sc_append_system(f"[INFO] Baud rate updated: {baudrate}")
            return

        try:
            self._serial_conn.baudrate = baudrate
            self._serial_baudrate = baudrate
            if hasattr(self, '_sc_status_baud_label'):
                self._sc_status_baud_label.setText(f"Baud rate: {baudrate}")
            self._sc_append_system(f"[INFO] Baud rate updated: {baudrate}")
        except Exception as e:
            self._sc_append_system(f"[ERROR] Failed to set baud rate: {e}")

    def _sc_on_auto_detect_toggled(self, checked):
        self._sc_baud_combo.setEditable(not checked)
        self._sc_baud_combo.setEnabled(not checked)
        self._sc_auto_baud_monitor.enabled = checked
        self._sc_auto_baud_monitor.runtime_redetect_enabled = checked
        if checked:
            self._sc_status_autobaud_label.setVisible(True)
            self._sc_status_autobaud_label.setText("AutoBaud: ON")
            if self._serial_connected:
                self._sc_auto_baud_pending_first_rx = True
                self._sc_auto_baud_initial_buf = bytearray()
                self._sc_auto_baud_initial_ts = time.perf_counter()
                self._sc_append_system("[INFO] Auto-detect enabled, waiting for RX data...")
        else:
            self._sc_status_autobaud_label.setVisible(False)
            self._sc_auto_baud_monitor.reset()
            self._sc_auto_baud_monitor.state = AutoBaudState.UNKNOWN
            self._sc_stop_auto_baud_scan()
            self._sc_auto_baud_pending_first_rx = False

    def _sc_start_auto_baud_scan(self, reason="initial"):
        if self._serial_conn is None or not self._serial_conn.is_open:
            self._sc_append_system("[WARN] Cannot auto-detect: serial not connected")
            return
        if self._sc_auto_baud_scan_thread is not None and self._sc_auto_baud_scan_thread.isRunning():
            return

        self._stop_serial_read()

        config = dict(AUTO_BAUD_CONFIG)
        worker = AutoBaudScanWorker(
            self._serial_conn, config, self._serial_baudrate
        )
        worker.set_recent_score_avg(self._sc_auto_baud_monitor.recent_score_avg)
        thread = QThread()
        worker.moveToThread(thread)

        if reason == "initial":
            thread.started.connect(worker.run_initial_scan)
        else:
            thread.started.connect(worker.run_runtime_rescan)

        worker.scan_finished.connect(self._sc_on_auto_baud_scan_finished)
        worker.scan_progress.connect(self._sc_on_auto_baud_progress)
        worker.state_changed.connect(self._sc_on_auto_baud_state_changed)
        worker.baudrate_changed.connect(self._sc_on_auto_baud_baudrate_changed)
        worker.scan_finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._sc_on_auto_baud_thread_cleanup)

        self._sc_auto_baud_scan_thread = thread
        self._sc_auto_baud_scan_worker = worker
        thread.start()

    def _sc_stop_auto_baud_scan(self):
        if self._sc_auto_baud_scan_worker is not None:
            self._sc_auto_baud_scan_worker.stop()
        if self._sc_auto_baud_scan_thread is not None and self._sc_auto_baud_scan_thread.isRunning():
            self._sc_auto_baud_scan_thread.quit()
            self._sc_auto_baud_scan_thread.wait(2000)
        self._sc_auto_baud_scan_thread = None
        self._sc_auto_baud_scan_worker = None

    def _sc_on_auto_baud_thread_cleanup(self):
        self._sc_auto_baud_scan_thread = None
        self._sc_auto_baud_scan_worker = None
        if self._serial_connected:
            self._start_serial_read()

    def _sc_on_auto_baud_scan_finished(self, result):
        if result.get("success"):
            baud = result["baudrate"]
            self._sc_auto_baud_monitor.state = AutoBaudState.LOCKED
            self._sc_auto_baud_monitor.reset()
            self._sc_auto_baud_monitor.mark_switch()
        else:
            reason = result.get("reason", "unknown")
            if reason == "no_baudrate_above_threshold":
                best = result.get("best")
                if best:
                    self._sc_append_system(
                        f"[WARN] No baudrate scored above threshold. Best: {best['baudrate']} score={best['score']}"
                    )
            self._sc_auto_baud_monitor.state = AutoBaudState.LOCKED
            self._sc_auto_baud_monitor.reset()

    def _sc_on_auto_baud_progress(self, msg):
        self._sc_append_system(msg)

    def _sc_on_auto_baud_state_changed(self, state_str):
        self._sc_auto_baud_monitor.state = AutoBaudState(state_str)
        label = self._sc_status_autobaud_label
        if state_str == AutoBaudState.SCANNING.value:
            label.setText("AutoBaud: SCANNING")
            label.setStyleSheet("color: #FBBF24;")
        elif state_str == AutoBaudState.SUSPECT.value:
            label.setText("AutoBaud: SUSPECT")
            label.setStyleSheet("color: #F87171;")
        elif state_str == AutoBaudState.LOCKED.value:
            label.setText("AutoBaud: LOCKED")
            label.setStyleSheet("color: #818CF8;")
        else:
            label.setText(f"AutoBaud: {state_str}")
            label.setStyleSheet("color: #94a3b8;")

    def _sc_on_auto_baud_baudrate_changed(self, baudrate):
        self._serial_baudrate = baudrate
        self._sc_baud_combo.setCurrentText(str(baudrate))
        if hasattr(self, '_sc_status_baud_label'):
            self._sc_status_baud_label.setText(f"Baud rate: {baudrate}")

    def _sc_on_pause(self, checked):
        self._sc_paused = checked
        self._sc_pause_btn.setText("Resume" if checked else "Pause")

    def _sc_on_stop(self):
        if self._serial_connected:
            self._sc_do_disconnect()

    def _sc_on_refresh(self):
        self._sc_port_combo.clear()
        if DEBUG_MOCK:
            self._sc_port_combo.addItem("[MOCK] COM99 - Mock Serial Device")
            self._sc_append_system("[INFO] Mock port refreshed")
            self._sc_try_restore_last_port()
            return
        try:
            ports = serial.tools.list_ports.comports()
            if ports:
                for p in ports:
                    self._sc_port_combo.addItem(f"{p.device} - {p.description}")
                self._sc_append_system(f"[INFO] Found {len(ports)} serial port(s)")
            else:
                self._sc_port_combo.addItem("No serial ports found")
                self._sc_append_system("[WARN] No serial ports found")
        except Exception as e:
            self._sc_append_system(f"[ERROR] Refresh failed: {e}")
        self._sc_try_restore_last_port()

    def _sc_try_restore_last_port(self):
        last_port = getattr(self, "_sc_last_port", "")
        if not last_port:
            return
        for i in range(self._sc_port_combo.count()):
            if self._sc_port_combo.itemText(i).startswith(last_port.split(" - ")[0].split()[0]):
                self._sc_port_combo.setCurrentIndex(i)
                break
            if last_port in self._sc_port_combo.itemText(i):
                self._sc_port_combo.setCurrentIndex(i)
                break

    def _sc_on_add_log_panel(self):
        if len(self._sc_extra_log_panels) >= 3:
            self._sc_append_system("[WARN] Maximum 4 LOG panels supported")
            return
        dlg = _AddLogPanelDialog(parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        panel_info = dlg.get_config()
        panel = self._build_extra_log_panel(panel_info)
        self._sc_extra_log_panels.append(panel)
        self._sc_relayout_log_panels()
        self._sc_remove_log_btn.setEnabled(True)
        self._sc_append_system(
            f"[INFO] New LOG panel: {panel_info.get('title', 'Log')} "
            f"({panel_info.get('port', 'N/A')} @ {panel_info.get('baudrate', 'N/A')})"
        )
        if panel_info.get("auto_connect", False):
            self._sc_extra_panel_connect(panel)

    def _sc_on_remove_log_panel(self):
        if not self._sc_extra_log_panels:
            return
        panel = self._sc_extra_log_panels.pop()
        self._sc_extra_panel_disconnect(panel)
        panel["frame"].setParent(None)
        panel["frame"].deleteLater()
        self._sc_relayout_log_panels()
        self._sc_remove_log_btn.setEnabled(len(self._sc_extra_log_panels) > 0)
        self._sc_append_system("[INFO] LOG panel removed")

    def _sc_relayout_log_panels(self):
        while self._sc_log_grid.count():
            item = self._sc_log_grid.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)

        self._sc_log_grid.setRowStretch(0, 0)
        self._sc_log_grid.setRowStretch(1, 0)
        self._sc_log_grid.setColumnStretch(0, 0)
        self._sc_log_grid.setColumnStretch(1, 0)

        total = 1 + len(self._sc_extra_log_panels)

        if total == 1:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
        elif total == 2:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[0]["frame"], 0, 1)
            self._sc_log_grid.setColumnStretch(0, 1)
            self._sc_log_grid.setColumnStretch(1, 1)
        elif total == 3:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[0]["frame"], 0, 1)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[1]["frame"], 1, 0)
            self._sc_log_grid.setColumnStretch(0, 1)
            self._sc_log_grid.setColumnStretch(1, 1)
            self._sc_log_grid.setRowStretch(0, 1)
            self._sc_log_grid.setRowStretch(1, 1)
        elif total == 4:
            self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[0]["frame"], 0, 1)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[1]["frame"], 1, 0)
            self._sc_log_grid.addWidget(self._sc_extra_log_panels[2]["frame"], 1, 1)
            self._sc_log_grid.setColumnStretch(0, 1)
            self._sc_log_grid.setColumnStretch(1, 1)
            self._sc_log_grid.setRowStretch(0, 1)
            self._sc_log_grid.setRowStretch(1, 1)

        self._sc_log_area.show()
        for p in self._sc_extra_log_panels:
            p["frame"].show()

    def _build_extra_log_panel(self, config):
        frame = QFrame()
        frame.setObjectName("scLogFrame")
        frame.setStyleSheet("""
            QFrame#scLogFrame {
                background-color: #020618;
                border: 1px solid #1e293b;
                border-radius: 4px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(6, 4, 6, 2)
        toolbar.setSpacing(4)

        icon_label = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "logs.svg"), "#cbd5e1", 12)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(12, 12))
        icon_label.setFixedSize(14, 14)
        icon_label.setStyleSheet("background: transparent;")
        toolbar.addWidget(icon_label)

        title_text = config.get("title", "Serial Log")
        title = QLabel(title_text)
        title.setStyleSheet(f"color: #FFFFFF; font-size: 14px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;")
        toolbar.addWidget(title)

        toolbar.addStretch()

        clear_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), "Clear", tone="log"
        )
        toolbar.addWidget(clear_btn)

        scroll_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"), "Auto-scroll", tone="log"
        )
        scroll_btn.setCheckable(True)
        scroll_btn.setChecked(True)
        toolbar.addWidget(scroll_btn)

        layout.addLayout(toolbar)

        log_edit = QTextEdit()
        log_edit.setReadOnly(True)
        log_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {_CLR_BG_LOG}; border: none; border-top: 1px solid {_CLR_BORDER};
                color: {_CLR_TEXT_BODY}; font-family: {_TERM_FONT}; font-size: 14px; font-weight: 400;
                padding: 6px 8px;
                selection-background-color: {_CLR_SELECTION_BG};
                selection-color: {_CLR_SELECTION_TEXT};
            }}
        """ + SCROLLBAR_STYLE)
        log_edit.document().setDefaultStyleSheet(
            "p, div { line-height: 150%; margin: 0; padding: 0; }"
        )
        log_edit.document().setMaximumBlockCount(5000)
        layout.addWidget(log_edit, 1)

        status_bar = QFrame()
        status_bar.setObjectName("scStatusBar")
        status_bar.setFixedHeight(28)
        status_bar.setStyleSheet(f"""
            QFrame#scStatusBar {{
                background-color: #050b1e;
                border-top: 1px solid #1e293b;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QLabel {{ font-size: 11px; font-family: {_TERM_FONT}; background: transparent; }}
        """)
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(10, 2, 10, 2)
        sb_layout.setSpacing(14)

        port_label = QLabel(f"Port: {config.get('port', 'Unconnected')}")
        port_label.setStyleSheet("color: #f43f5e;")
        sb_layout.addWidget(port_label)

        baud_label = QLabel(f"Baud rate: {config.get('baudrate', '-')}")
        baud_label.setStyleSheet("color: #94a3b8;")
        sb_layout.addWidget(baud_label)

        rx_label = QLabel("RX: 0 B")
        rx_label.setStyleSheet(f"color: {_CLR_RX};")
        sb_layout.addWidget(rx_label)

        tx_label = QLabel("TX: 0 B")
        tx_label.setStyleSheet(f"color: {_CLR_TX};")
        sb_layout.addWidget(tx_label)

        sb_layout.addStretch()
        layout.addWidget(status_bar)

        panel = {
            "frame": frame,
            "log_edit": log_edit,
            "clear_btn": clear_btn,
            "scroll_btn": scroll_btn,
            "port_label": port_label,
            "baud_label": baud_label,
            "rx_label": rx_label,
            "tx_label": tx_label,
            "config": config,
            "conn": None,
            "read_thread": None,
            "read_worker": None,
            "rx_bytes": 0,
            "tx_bytes": 0,
            "auto_scroll": True,
            "all_logs": [],
            "pending_html": [],
        }

        clear_btn.clicked.connect(lambda: self._sc_extra_panel_clear(panel))
        scroll_btn.clicked.connect(lambda c: panel.__setitem__("auto_scroll", c))

        if log_edit.verticalScrollBar():
            log_edit.verticalScrollBar().valueChanged.connect(
                lambda val, p=panel: self._sc_extra_panel_on_scroll(p, val)
            )

        return panel

    def _sc_extra_panel_clear(self, panel):
        panel["all_logs"].clear()
        panel["pending_html"].clear()
        panel["log_edit"].clear()
        panel["rx_bytes"] = 0
        panel["tx_bytes"] = 0
        panel["rx_label"].setText("RX: 0 B")
        panel["tx_label"].setText("TX: 0 B")
        panel["auto_scroll"] = True
        panel["scroll_btn"].setChecked(True)

    def _sc_extra_panel_on_scroll(self, panel, value):
        sb = panel["log_edit"].verticalScrollBar()
        if sb and sb.maximum() > 0:
            at_bottom = value >= sb.maximum() - 5
            if not at_bottom and panel["auto_scroll"]:
                panel["auto_scroll"] = False
                panel["scroll_btn"].setChecked(False)
            elif at_bottom and not panel["auto_scroll"]:
                panel["auto_scroll"] = True
                panel["scroll_btn"].setChecked(True)

    def _sc_extra_panel_connect(self, panel):
        config = panel["config"]
        port = config.get("port", "")
        baudrate = config.get("baudrate", 115200)

        if not port:
            return

        if DEBUG_MOCK:
            panel["conn"] = None
            panel["port_label"].setText(f"Port: MOCK")
            panel["port_label"].setStyleSheet(f"color: #34d399; font-size: 11px; font-family: {_TERM_FONT}; background: transparent;")
            self._sc_extra_panel_append_log(panel, "[INFO] Mock connected", _CLR_TEXT_INFO)
            return

        try:
            databit = config.get("databit", 8)
            stopbit_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}
            stopbits = stopbit_map.get(config.get("stopbit", "1"), serial.STOPBITS_ONE)
            parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD,
                          "Mark": serial.PARITY_MARK, "Space": serial.PARITY_SPACE}
            parity = parity_map.get(config.get("parity", "None"), serial.PARITY_NONE)
            flow = config.get("flow", "None")

            conn = serial.Serial(
                port=port, baudrate=baudrate, bytesize=databit,
                stopbits=stopbits, parity=parity,
                xonxoff=(flow == "XON/XOFF"), rtscts=(flow == "RTS/CTS"),
                timeout=0.1,
            )
            panel["conn"] = conn
            panel["port_label"].setText(f"Port: {port}")
            panel["port_label"].setStyleSheet(f"color: #34d399; font-size: 11px; font-family: {_TERM_FONT}; background: transparent;")
            self._sc_extra_panel_append_log(panel, f"[INFO] Connected: {port} @ {baudrate}", _CLR_TEXT_INFO)
            self._sc_extra_panel_start_read(panel)
        except Exception as e:
            self._sc_extra_panel_append_log(panel, f"[ERROR] Connection failed: {e}", "#f43f5e")

    def _sc_extra_panel_disconnect(self, panel):
        if panel.get("read_worker"):
            panel["read_worker"].stop()
        if panel.get("read_thread") and panel["read_thread"].isRunning():
            panel["read_thread"].quit()
            panel["read_thread"].wait(2000)
        panel["read_thread"] = None
        panel["read_worker"] = None
        try:
            if panel["conn"] and panel["conn"].is_open:
                panel["conn"].close()
        except Exception:
            pass
        panel["conn"] = None

    def _sc_extra_panel_start_read(self, panel):
        if panel["conn"] is None or not panel["conn"].is_open:
            return
        worker = _SerialReadWorker(panel["conn"])
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.data_received.connect(lambda data, p=panel: self._sc_extra_panel_on_data(p, data))
        worker.error.connect(lambda err, p=panel: self._sc_extra_panel_append_log(p, f"[ERROR] {err}", _CLR_ERROR))
        panel["read_thread"] = thread
        panel["read_worker"] = worker
        thread.start()

    def _sc_extra_panel_on_data(self, panel, data: bytes):
        panel["rx_bytes"] += len(data)
        panel["rx_label"].setText(self._sc_format_bytes("RX", panel["rx_bytes"]))
        display = data.decode("utf-8", errors="replace")
        for line in display.splitlines():
            if line.strip():
                self._sc_extra_panel_append_log(panel, f"[RX] {line}", _CLR_RX)

    def _sc_extra_panel_append_log(self, panel, message, color=_CLR_TEXT_BODY):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ts_html = f'<span style="color:{_CLR_TEXT_TIME};">{ts}</span> '
        html = f'{ts_html}<span style="color:{color};">{escaped}</span>'
        panel["all_logs"].append((message, html))
        panel["pending_html"].append(html)

    def _sc_flush_extra_panels(self):
        for panel in self._sc_extra_log_panels:
            if not panel["pending_html"]:
                continue
            batch = panel["pending_html"][:200]
            panel["pending_html"] = panel["pending_html"][200:]
            log_edit = panel["log_edit"]
            log_edit.setUpdatesEnabled(False)
            cursor = log_edit.textCursor()
            cursor.beginEditBlock()
            for html in batch:
                log_edit.append(html)
            cursor.endEditBlock()
            log_edit.setUpdatesEnabled(True)
            if panel["auto_scroll"]:
                sb = log_edit.verticalScrollBar()
                if sb:
                    sb.setValue(sb.maximum())

    def _sc_on_sidebar_toggle(self, checked):
        self._sc_sidebar_visible = checked
        self._sc_sidebar_widget.setVisible(checked)
        if checked:
            sizes = self._sc_body_splitter.sizes()
            if sizes and sizes[0] < self._sc_sidebar_min_width:
                center_width = max(sizes[1], 600) if len(sizes) > 1 else 600
                self._sc_body_splitter.setSizes([self._sc_sidebar_default_width, center_width])

    def _sc_open_settings_dialog(self):
        dlg = _SerialSettingsDialog(self)

        dlg.port_combo.clear()
        for i in range(self._sc_port_combo.count()):
            dlg.port_combo.addItem(self._sc_port_combo.itemText(i))
        dlg.port_combo.setCurrentIndex(self._sc_port_combo.currentIndex())

        dlg.baud_combo.setCurrentText(self._sc_baud_combo.currentText())

        dlg.databit_combo.setCurrentText(self._sc_databit_combo.currentText())
        dlg.flow_combo.setCurrentText(self._sc_flow_combo.currentText())
        dlg.stopbit_combo.setCurrentText(self._sc_stopbit_combo.currentText())
        dlg.parity_combo.setCurrentText(self._sc_parity_combo.currentText())

        dlg.rx_hex_toggle.set_value("HEX" if self._sc_rx_display_hex else "ASCII")
        dlg.show_time_cb.setChecked(self._sc_show_timestamp)
        dlg.rx_max_lines_spin.setValue(getattr(self, '_sc_max_log_lines', 10000))

        dlg.tx_hex_toggle.set_value("HEX" if self._sc_tx_display_hex else "ASCII")
        dlg.auto_resend_cb.setChecked(self._sc_auto_resend)
        dlg.resend_spin.setValue(self._sc_resend_spin.value())
        idx = self._sc_ending_combo.currentIndex()
        if 0 <= idx < dlg.ending_combo.count():
            dlg.ending_combo.setCurrentIndex(idx)
        dlg.show_send_cb.setChecked(self._sc_show_send)
        dlg.line_by_line_cb.setChecked(self._sc_line_by_line)

        dlg.log_auto_save_cb.setChecked(getattr(self, '_sc_log_auto_save', False))
        dlg.log_save_path_edit.setText(getattr(self, '_sc_log_save_path', ''))

        dlg.display_font_combo.setCurrentText(getattr(self, '_sc_display_font', 'Consolas'))
        dlg.display_font_size_spin.setValue(getattr(self, '_sc_display_font_size', 11))
        dlg.display_auto_scroll_cb.setChecked(self._sc_auto_scroll)
        dlg.display_word_wrap_cb.setChecked(getattr(self, '_sc_word_wrap', True))

        dlg.auto_detect_enable_cb.setChecked(self._sc_auto_detect_cb.isChecked())
        dlg.auto_detect_runtime_cb.setChecked(self._sc_auto_baud_monitor.runtime_redetect_enabled)
        dlg.auto_detect_candidates_edit.setText(
            ", ".join(str(b) for b in self._sc_auto_baud_monitor._config["candidate_baudrates"])
        )
        dlg.auto_detect_lock_spin.setValue(self._sc_auto_baud_monitor._config["lock_threshold"])
        dlg.auto_detect_bad_spin.setValue(self._sc_auto_baud_monitor._config["bad_threshold"])
        dlg.auto_detect_bad_windows_spin.setValue(self._sc_auto_baud_monitor._config["bad_windows_to_suspect"])
        dlg.auto_detect_suspect_windows_spin.setValue(self._sc_auto_baud_monitor._config["suspect_windows_to_scan"])
        dlg.auto_detect_window_ms_spin.setValue(self._sc_auto_baud_monitor._config["monitor_window_max_time_ms"])
        dlg.auto_detect_cooldown_spin.setValue(self._sc_auto_baud_monitor._config["switch_cooldown_ms"])
        dlg.auto_detect_margin_spin.setValue(self._sc_auto_baud_monitor._config["switch_score_margin"])
        dlg.auto_detect_confirm_spin.setValue(self._sc_auto_baud_monitor._config["confirm_scan_rounds"])

        if dlg.exec() == QDialog.Accepted:
            self._sc_port_combo.setCurrentIndex(dlg.port_combo.currentIndex())
            self._sc_baud_combo.setCurrentText(dlg.baud_combo.currentText())
            self._sc_databit_combo.setCurrentText(dlg.databit_combo.currentText())
            self._sc_flow_combo.setCurrentText(dlg.flow_combo.currentText())
            self._sc_stopbit_combo.setCurrentText(dlg.stopbit_combo.currentText())
            self._sc_parity_combo.setCurrentText(dlg.parity_combo.currentText())

            rx_val = dlg.rx_hex_toggle.value()
            self._sc_rx_display_hex = rx_val == "HEX"
            self._sc_rx_toggle.set_value(rx_val)

            self._sc_show_timestamp = dlg.show_time_cb.isChecked()
            self._sc_rx_show_time_cb.setChecked(self._sc_show_timestamp)
            self._sc_max_log_lines = dlg.rx_max_lines_spin.value()

            tx_val = dlg.tx_hex_toggle.value()
            self._sc_tx_display_hex = tx_val == "HEX"
            self._sc_tx_toggle.set_value(tx_val)

            self._sc_auto_resend_cb.setChecked(dlg.auto_resend_cb.isChecked())
            self._sc_resend_spin.setValue(dlg.resend_spin.value())

            ending_idx = dlg.ending_combo.currentIndex()
            self._sc_ending_combo.setCurrentIndex(ending_idx)

            self._sc_show_send_cb.setChecked(dlg.show_send_cb.isChecked())
            self._sc_line_by_line_cb.setChecked(dlg.line_by_line_cb.isChecked())

            self._sc_log_auto_save = dlg.log_auto_save_cb.isChecked()
            self._sc_log_save_path = dlg.log_save_path_edit.text()

            font_family = dlg.display_font_combo.currentText()
            font_size = dlg.display_font_size_spin.value()
            self._sc_display_font = font_family
            self._sc_display_font_size = font_size
            self._sc_log_edit.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {_CLR_BG_LOG}; border: none; border-top: 1px solid {_CLR_BORDER};
                    color: {_CLR_TEXT_BODY}; font-family: {font_family}, {_TERM_FONT}; font-size: {font_size}px; font-weight: 400;
                    padding: 4px 6px; line-height: 1.5;
                    selection-background-color: {_CLR_SELECTION_BG};
                    selection-color: {_CLR_SELECTION_TEXT};
                }}
            """ + SCROLLBAR_STYLE)

            self._sc_auto_scroll = dlg.display_auto_scroll_cb.isChecked()
            self._sc_scroll_lock_btn.setChecked(self._sc_auto_scroll)

            self._sc_word_wrap = dlg.display_word_wrap_cb.isChecked()
            from PySide6.QtWidgets import QTextEdit as _QTE
            self._sc_log_edit.setLineWrapMode(
                _QTE.WidgetWidth if self._sc_word_wrap else _QTE.NoWrap
            )

            self._sc_apply_auto_detect_settings(dlg)

    def _sc_apply_auto_detect_settings(self, dlg):
        enable = dlg.auto_detect_enable_cb.isChecked()
        runtime = dlg.auto_detect_runtime_cb.isChecked()

        candidates_text = dlg.auto_detect_candidates_edit.text().strip()
        candidates = []
        for part in candidates_text.replace(";", ",").split(","):
            part = part.strip()
            if part.isdigit():
                candidates.append(int(part))
        if not candidates:
            candidates = list(AUTO_BAUD_CONFIG["candidate_baudrates"])

        config = dict(self._sc_auto_baud_monitor._config)
        config["candidate_baudrates"] = candidates
        config["lock_threshold"] = dlg.auto_detect_lock_spin.value()
        config["bad_threshold"] = dlg.auto_detect_bad_spin.value()
        config["bad_windows_to_suspect"] = dlg.auto_detect_bad_windows_spin.value()
        config["suspect_windows_to_scan"] = dlg.auto_detect_suspect_windows_spin.value()
        config["monitor_window_max_time_ms"] = dlg.auto_detect_window_ms_spin.value()
        config["switch_cooldown_ms"] = dlg.auto_detect_cooldown_spin.value()
        config["switch_score_margin"] = dlg.auto_detect_margin_spin.value()
        config["confirm_scan_rounds"] = dlg.auto_detect_confirm_spin.value()

        self._sc_auto_baud_monitor.update_config(config)
        self._sc_auto_baud_monitor.runtime_redetect_enabled = runtime

        if enable != self._sc_auto_detect_cb.isChecked():
            self._sc_auto_detect_cb.setChecked(enable)

    def _sc_on_filter_toggle(self, checked):
        self._sc_filter_row.setVisible(checked)
        if not checked:
            self._sc_filter_input.clear()
            self._sc_filter_match_label.setText("")
            self._sc_filter_dirty = False
            self._sc_filter_last_count = len(self._sc_all_logs)
            self._sc_reset_applied_filter()
            self._sc_rebuild_log_view()

    def _sc_reset_applied_filter(self):
        self._sc_filter_applied_pattern = ""
        self._sc_filter_applied_use_regex = False
        self._sc_filter_applied_case = False
        self._sc_filter_applied_invert = False
        self._sc_filter_applied_before = 0
        self._sc_filter_applied_after = 0

    def _sc_filter_inputs_match_applied(self):
        return (
            self._sc_filter_input.text().strip() == self._sc_filter_applied_pattern
            and self._sc_filter_regex_cb.isChecked() == self._sc_filter_applied_use_regex
            and self._sc_filter_case_cb.isChecked() == self._sc_filter_applied_case
            and self._sc_filter_invert_cb.isChecked() == self._sc_filter_applied_invert
            and self._sc_filter_before_spin.value() == self._sc_filter_applied_before
            and self._sc_filter_after_spin.value() == self._sc_filter_applied_after
        )

    def _sc_update_pending_hint(self):
        if not self._sc_filter_row.isVisible():
            return
        if self._sc_filter_inputs_match_applied():
            return
        self._sc_filter_match_label.setText("Press Enter to apply")

    def _sc_on_filter_input_changed(self, _text=None):
        self._sc_update_pending_hint()

    def _sc_on_filter_option_changed(self, *_args):
        self._sc_update_pending_hint()

    def _sc_apply_filter(self, _text=None):
        self._sc_filter_dirty = False
        pattern = self._sc_filter_input.text().strip()
        self._sc_filter_applied_pattern = pattern
        self._sc_filter_applied_use_regex = self._sc_filter_regex_cb.isChecked()
        self._sc_filter_applied_case = self._sc_filter_case_cb.isChecked()
        self._sc_filter_applied_invert = self._sc_filter_invert_cb.isChecked()
        self._sc_filter_applied_before = self._sc_filter_before_spin.value()
        self._sc_filter_applied_after = self._sc_filter_after_spin.value()

        if not pattern:
            self._sc_filter_last_count = len(self._sc_all_logs)
            self._sc_rebuild_log_view()
            self._sc_filter_match_label.setText("")
            return

        use_regex = self._sc_filter_applied_use_regex
        case_sensitive = self._sc_filter_applied_case
        invert = self._sc_filter_applied_invert
        before = self._sc_filter_applied_before
        after = self._sc_filter_applied_after

        matched_indices = self._sc_get_matched_indices(
            pattern, use_regex, case_sensitive, invert
        )
        self._sc_filter_match_label.setText(f"Matched: {len(matched_indices)} lines")

        matched_set = set(matched_indices)
        visible = set()
        for idx in matched_indices:
            start = max(0, idx - before)
            end = min(len(self._sc_all_logs) - 1, idx + after)
            for i in range(start, end + 1):
                visible.add(i)

        self._sc_log_edit.setUpdatesEnabled(False)
        self._sc_log_edit.clear()
        cursor = self._sc_log_edit.textCursor()
        cursor.beginEditBlock()
        prev_shown = -2
        for i in sorted(visible):
            if before > 0 or after > 0:
                if prev_shown >= 0 and i - prev_shown > 1:
                    self._sc_log_edit.append(
                        f'<span style="color:{_CLR_TEXT_LINENO};">  ───</span>'
                    )
            if i in matched_set and not invert:
                self._sc_log_edit.append(
                    self._sc_html_with_filter_highlight(
                        self._sc_all_logs[i][1], pattern, use_regex, case_sensitive
                    )
                )
            else:
                self._sc_log_edit.append(self._sc_all_logs[i][1])
            prev_shown = i
        cursor.endEditBlock()
        self._sc_log_edit.setUpdatesEnabled(True)
        self._sc_filter_last_count = len(self._sc_all_logs)
        if self._sc_auto_scroll:
            self._sc_scroll_to_bottom()

    def _sc_rebuild_log_view(self):
        self._sc_log_edit.setUpdatesEnabled(False)
        self._sc_log_edit.clear()
        cursor = self._sc_log_edit.textCursor()
        cursor.beginEditBlock()
        for _raw, html in self._sc_all_logs:
            self._sc_log_edit.append(html)
        cursor.endEditBlock()
        self._sc_log_edit.setUpdatesEnabled(True)
        if self._sc_auto_scroll:
            self._sc_scroll_to_bottom()

    def _sc_is_filter_active(self):
        return (self._sc_filter_row.isVisible()
                and bool(self._sc_filter_applied_pattern))

    def _sc_get_matched_indices(self, pattern, use_regex, case_sensitive, invert):
        matched = []
        compiled = None
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(pattern, flags)
            except re.error:
                return matched

        for i, (raw, _html) in enumerate(self._sc_all_logs):
            if compiled is not None:
                hit = bool(compiled.search(raw))
            elif case_sensitive:
                hit = pattern in raw
            else:
                hit = pattern.lower() in raw.lower()
            if invert:
                hit = not hit
            if hit:
                matched.append(i)
        return matched

    @staticmethod
    def _sc_html_with_filter_highlight(html: str, pattern: str,
                                       use_regex: bool, case_sensitive: bool) -> str:
        if not pattern:
            return html

        compiled = None
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(pattern, flags)
            except re.error:
                return html
        else:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(re.escape(pattern), flags)
            except re.error:
                return html

        wrap_open = (
            f'<span style="background-color:{_CLR_FILTER_BG};'
            f'color:{_CLR_FILTER_TEXT};'
            f'border:1px solid {_CLR_FILTER_BORDER};'
            f'border-radius:2px;padding:0 1px;">'
        )
        wrap_close = '</span>'

        parts = re.split(r'(<[^>]*>)', html)
        for idx, seg in enumerate(parts):
            if not seg or seg.startswith('<'):
                continue
            try:
                parts[idx] = compiled.sub(
                    lambda m: f'{wrap_open}{m.group(0)}{wrap_close}', seg
                )
            except re.error:
                continue
        return ''.join(parts)

    def _sc_copy_logs(self):
        cb = QApplication.clipboard()
        if not cb:
            return
        lines = []
        if self._sc_is_filter_active():
            pattern = self._sc_filter_applied_pattern
            use_regex = self._sc_filter_applied_use_regex
            case_sensitive = self._sc_filter_applied_case
            invert = self._sc_filter_applied_invert
            before = self._sc_filter_applied_before
            after = self._sc_filter_applied_after
            matched_indices = self._sc_get_matched_indices(
                pattern, use_regex, case_sensitive, invert
            )
            visible = set()
            for idx in matched_indices:
                start = max(0, idx - before)
                end = min(len(self._sc_all_logs) - 1, idx + after)
                for i in range(start, end + 1):
                    visible.add(i)
            prev_shown = -2
            for i in sorted(visible):
                if (before > 0 or after > 0) and prev_shown >= 0 and i - prev_shown > 1:
                    lines.append("  ───")
                lines.append(self._sc_all_logs[i][0])
                prev_shown = i
        else:
            for raw, _html in self._sc_all_logs:
                lines.append(raw)
        cb.setText("\n".join(lines))

    def _sc_export_logs(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Logs", f"serial_log_{ts}.txt", "Text Files (*.txt);;All Files (*)"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                for raw, _ in self._sc_all_logs:
                    f.write(raw + "\n")

    def _sc_clear_logs(self):
        self._sc_all_logs.clear()
        self._sc_pending_html.clear()
        self._sc_log_edit.clear()
        self._sc_rx_bytes = 0
        self._sc_tx_bytes = 0
        self._sc_rx_line_buf = ""
        self._sc_status_rx_label.setText("RX: 0 B")
        self._sc_status_tx_label.setText("TX: 0 B")
        self._sc_filter_last_count = 0
        self._sc_filter_dirty = False
        self._sc_filter_match_label.setText("")
        self._sc_reset_applied_filter()
        self._sc_auto_scroll = True
        self._sc_scroll_lock_btn.setChecked(True)

    def _sc_on_user_scroll(self, value):
        sb = self._sc_log_edit.verticalScrollBar()
        if sb and sb.maximum() > 0:
            at_bottom = value >= sb.maximum() - 5
            if not at_bottom and self._sc_auto_scroll:
                self._sc_auto_scroll = False
                self._sc_scroll_lock_btn.setChecked(False)
            elif at_bottom and not self._sc_auto_scroll:
                self._sc_auto_scroll = True
                self._sc_scroll_lock_btn.setChecked(True)

    def _sc_scroll_to_bottom(self):
        sb = self._sc_log_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _sc_on_send(self):
        text = self._sc_send_input.text()
        if not text:
            return

        if self._sc_line_by_line:
            lines = text.split("\\n")
        else:
            lines = [text]

        for line in lines:
            if self._sc_tx_display_hex:
                try:
                    data = bytes.fromhex(line.replace(" ", ""))
                except ValueError:
                    self._sc_append_system(f"[ERROR] Invalid HEX: {line}")
                    return
            else:
                data = (line + self._sc_line_ending).encode("utf-8")

            ok = self.serial_send(data)
            if ok:
                self._sc_tx_bytes += len(data)
                self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))
                if self._sc_show_send:
                    display = line if not self._sc_tx_display_hex else data.hex(' ')
                    self._sc_append_log(f"[TX] {display}", _CLR_TX)
            else:
                self._sc_append_system("[ERROR] Send failed, serial not connected")

        if text not in self._sc_send_history:
            self._sc_send_history.insert(0, text)
            if len(self._sc_send_history) > 50:
                self._sc_send_history.pop()
            self._sc_history_combo.blockSignals(True)
            self._sc_history_combo.clear()
            self._sc_history_combo.addItems(self._sc_send_history)
            self._sc_history_combo.setCurrentIndex(-1)
            self._sc_history_combo.blockSignals(False)

        self._sc_send_input.clear()

    def _sc_on_data_received(self, data: bytes):
        if self._sc_paused:
            return
        self._sc_rx_bytes += len(data)
        self._sc_status_rx_label.setText(self._sc_format_bytes("RX", self._sc_rx_bytes))

        if self._sc_rx_display_hex:
            display = data.hex(' ')
            for line in display.splitlines():
                if line.strip():
                    self._sc_append_log(f"[RX] {line}", _CLR_RX)
        else:
            display = data.decode("utf-8", errors="replace")
            display = display.replace("\x00", "")
            display = "".join(
                ch if ch == "\n" or ch == "\r" or ch == "\t" or (ord(ch) >= 0x20) else ""
                for ch in display
            )

            self._sc_rx_line_buf += display
            while "\n" in self._sc_rx_line_buf:
                line, self._sc_rx_line_buf = self._sc_rx_line_buf.split("\n", 1)
                line = line.rstrip("\r")
                if line.strip():
                    self._sc_append_log(f"[RX] {line}", _CLR_RX)

            if self._sc_rx_line_buf and self._sc_rx_auto_flush_cb.isChecked():
                self._sc_rx_flush_timer.start(self._sc_rx_auto_flush_spin.value())
            else:
                self._sc_rx_flush_timer.stop()

        self._sc_feed_auto_baud_monitor(data)

    def _sc_flush_rx_line_buf(self):
        if self._sc_rx_line_buf:
            line = self._sc_rx_line_buf.rstrip("\r")
            self._sc_rx_line_buf = ""
            if line.strip():
                self._sc_append_log(f"[RX] {line}", _CLR_RX)

    def _sc_feed_auto_baud_monitor(self, data: bytes):
        monitor = self._sc_auto_baud_monitor
        if not monitor.enabled:
            return
        if self._sc_auto_baud_pending_first_rx:
            self._sc_auto_baud_initial_buf.extend(data)
            cfg = monitor._config
            buf_len = len(self._sc_auto_baud_initial_buf)
            elapsed_ms = (time.perf_counter() - self._sc_auto_baud_initial_ts) * 1000
            if buf_len >= cfg["scan_sample_bytes"] or elapsed_ms >= cfg["scan_timeout_ms"]:
                self._sc_auto_baud_pending_first_rx = False
                sample = bytes(self._sc_auto_baud_initial_buf)
                self._sc_auto_baud_initial_buf = bytearray()
                s = score_rx_data(sample)
                if s is not None and s >= cfg["lock_threshold"]:
                    self._sc_append_system(
                        f"[INFO] Current baudrate {self._serial_baudrate} score={s}, locked."
                    )
                    monitor.state = AutoBaudState.LOCKED
                    monitor.reset()
                    self._sc_on_auto_baud_state_changed(AutoBaudState.LOCKED.value)
                else:
                    score_info = f"score={s}" if s is not None else "no data"
                    self._sc_append_system(
                        f"[INFO] Current baudrate {self._serial_baudrate} {score_info}, scanning candidates..."
                    )
                    self._sc_start_auto_baud_scan("initial")
            return
        monitor.hex_mode = self._sc_rx_display_hex
        result = monitor.on_rx_data(data)
        if result is None:
            return
        action = result.get("action")
        if action == "suspect":
            self._sc_append_system("[INFO] RX quality degraded. Enter SUSPECT state.")
            self._sc_on_auto_baud_state_changed(AutoBaudState.SUSPECT.value)
        elif action == "recovered":
            self._sc_append_system("[INFO] RX quality recovered.")
            self._sc_on_auto_baud_state_changed(AutoBaudState.LOCKED.value)
        elif action == "scan_needed":
            self._sc_append_system("[INFO] Sustained RX quality issue. Starting rescan...")
            self._sc_start_auto_baud_scan("runtime")

    def _sc_on_auto_resend_toggled(self, checked):
        self._sc_auto_resend = checked
        if checked:
            self._sc_resend_timer.setInterval(self._sc_resend_spin.value())
            self._sc_resend_timer.start()
        else:
            self._sc_resend_timer.stop()

    def _sc_on_resend_tick(self):
        text = self._sc_send_input.text()
        if text and self._serial_connected:
            if self._sc_tx_display_hex:
                try:
                    data = bytes.fromhex(text.replace(" ", ""))
                except ValueError:
                    return
            else:
                data = (text + self._sc_line_ending).encode("utf-8")
            ok = self.serial_send(data)
            if ok:
                self._sc_tx_bytes += len(data)
                self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))

    # --- quick commands (项目 -> 分组 -> 指令) ---

    @staticmethod
    def _sc_qc_default_data():
        return {
            "version": "1.0",
            "last_project_id": "project_default",
            "last_group_id": "group_default",
            "projects": [
                {
                    "id": "project_default",
                    "name": "默认项目",
                    "groups": [
                        {
                            "id": "group_default",
                            "name": "默认分组",
                            "commands": [],
                        }
                    ],
                }
            ],
        }

    @staticmethod
    def _sc_qc_gen_id(prefix: str) -> str:
        return f"{prefix}_{_uuid.uuid4().hex[:8]}"

    def _sc_qc_get_project(self, project_id):
        if not project_id:
            return None
        for p in self._sc_qc_data.get("projects", []):
            if p.get("id") == project_id:
                return p
        return None

    def _sc_qc_get_group(self, project, group_id):
        if not project or not group_id:
            return None
        for g in project.get("groups", []):
            if g.get("id") == group_id:
                return g
        return None

    def _sc_qc_current_project(self):
        return self._sc_qc_get_project(self._sc_qc_data.get("last_project_id"))

    def _sc_qc_current_group(self):
        return self._sc_qc_get_group(
            self._sc_qc_current_project(), self._sc_qc_data.get("last_group_id")
        )

    def _sc_qc_ensure_selection(self):
        projects = self._sc_qc_data.get("projects", [])
        if not projects:
            self._sc_qc_data = self._sc_qc_default_data()
            projects = self._sc_qc_data["projects"]

        project = self._sc_qc_current_project()
        if project is None:
            project = projects[0]
            self._sc_qc_data["last_project_id"] = project.get("id", "")

        groups = project.setdefault("groups", [])
        if not groups:
            groups.append({
                "id": self._sc_qc_gen_id("group"),
                "name": "默认分组",
                "commands": [],
            })
        group = self._sc_qc_get_group(project, self._sc_qc_data.get("last_group_id"))
        if group is None:
            group = groups[0]
            self._sc_qc_data["last_group_id"] = group.get("id", "")

    def _sc_qc_refresh_all(self):
        self._sc_qc_ensure_selection()
        self._sc_qc_refresh_project_tabs()
        self._sc_qc_refresh_group_combo()
        self._sc_refresh_quick_buttons()

    _SC_QC_ADD_TAB_MARK = "__add__"

    def _sc_qc_refresh_project_tabs(self):
        tabs = self._sc_qc_project_tabs
        tabs.blockSignals(True)
        while tabs.count() > 0:
            tabs.removeTab(0)
        active_index = 0
        projects = self._sc_qc_data.get("projects", [])
        for i, p in enumerate(projects):
            tabs.addTab(p.get("name", "未命名"))
            tabs.setTabData(i, p.get("id", ""))
            if p.get("id") == self._sc_qc_data.get("last_project_id"):
                active_index = i
        # 末尾追加 "+" 加号 tab，单击即新增项目
        plus_index = tabs.addTab("+")
        tabs.setTabData(plus_index, self._SC_QC_ADD_TAB_MARK)
        tabs.setTabToolTip(plus_index, "新增项目")
        if projects:
            tabs.setCurrentIndex(active_index)
        tabs.blockSignals(False)

    def _sc_qc_refresh_group_combo(self):
        combo = self._sc_qc_group_combo
        combo.blockSignals(True)
        combo.clear()
        project = self._sc_qc_current_project()
        active_index = 0
        if project:
            for i, g in enumerate(project.get("groups", [])):
                combo.addItem(g.get("name", "未命名"), g.get("id", ""))
                if g.get("id") == self._sc_qc_data.get("last_group_id"):
                    active_index = i
        if combo.count() > 0:
            combo.setCurrentIndex(active_index)
        combo.blockSignals(False)

    def _sc_qc_clear_button_grid(self):
        layout = self._sc_qc_btn_layout
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()

    def _sc_refresh_quick_buttons(self):
        self._sc_qc_clear_button_grid()
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        cols = 6
        for idx, entry in enumerate(commands):
            name = entry.get("name", "") or entry.get("content", "")
            content = entry.get("content", "")
            btn = _QuickCmdButton(name if name else content)
            btn.setObjectName("quickCommandButton")
            btn.set_command_index(idx)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.StrongFocus)
            btn.setToolTip(
                f"Name: {name}\nContent: {content}\n"
                f"Type: {entry.get('send_type', 'text')}  "
                f"Encoding: {entry.get('encoding', 'ascii')}  "
                f"LineEnding: {repr(entry.get('line_ending', ''))}"
            )
            btn.clicked.connect(
                lambda checked=False, e=entry: self._sc_send_quick(e)
            )
            # 右键菜单：编辑 / 删除
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, i=idx: self._sc_qc_on_cmd_btn_context_menu(b, pos, i)
            )
            # 单按钮覆盖：颜色 / hover / pressed 完全对齐 LOG_FastCommand.md 推荐风格
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #172033;
                    color: #e5e7eb;
                    border: 1px solid #334155;
                    border-radius: 7px;
                    padding: 6px 13px;
                    min-height: 28px;
                    min-width: 56px;
                    font-size: 12px;
                    font-weight: 500;
                    font-family: {_UI_FONT};
                }}
                QPushButton:hover {{
                    background-color: #25344d;
                    border-color: #3b82f6;
                    color: #ffffff;
                }}
                QPushButton:focus {{
                    background-color: #25344d;
                    border-color: #818CF8;
                    color: #ffffff;
                }}
                QPushButton:pressed {{
                    background-color: #1d4ed8;
                    border-color: #60a5fa;
                }}
            """)
            row, col = divmod(idx, cols)
            self._sc_qc_btn_layout.addWidget(btn, row, col)
        self._sc_qc_btn_layout.setRowStretch(
            (len(commands) // cols) + 1, 1
        )
        self._sc_qc_btn_layout.setColumnStretch(cols, 1)

    # --- 切换 ---

    def _sc_qc_on_project_tab_changed(self, index):
        if index < 0 or index >= self._sc_qc_project_tabs.count():
            return
        project_id = self._sc_qc_project_tabs.tabData(index)
        # 命中末尾 "+" 加号 tab：触发新增项目；若用户取消则回切到原项目
        if project_id == self._SC_QC_ADD_TAB_MARK:
            prev_id = self._sc_qc_data.get("last_project_id", "")
            created = self._sc_qc_add_project()
            if not created:
                tabs = self._sc_qc_project_tabs
                tabs.blockSignals(True)
                restore_index = 0
                for i in range(tabs.count()):
                    if tabs.tabData(i) == prev_id:
                        restore_index = i
                        break
                tabs.setCurrentIndex(restore_index)
                tabs.blockSignals(False)
            return
        if not project_id or project_id == self._sc_qc_data.get("last_project_id"):
            return
        self._sc_qc_data["last_project_id"] = project_id
        project = self._sc_qc_get_project(project_id)
        if project is not None:
            groups = project.get("groups", [])
            self._sc_qc_data["last_group_id"] = groups[0].get("id", "") if groups else ""
        self._sc_qc_ensure_selection()
        self._sc_qc_refresh_group_combo()
        self._sc_refresh_quick_buttons()
        self._sc_qc_save_data()

    def _sc_qc_on_group_changed(self, index):
        if index < 0:
            return
        group_id = self._sc_qc_group_combo.itemData(index)
        if not group_id or group_id == self._sc_qc_data.get("last_group_id"):
            return
        self._sc_qc_data["last_group_id"] = group_id
        self._sc_refresh_quick_buttons()
        self._sc_qc_save_data()

    # --- 项目 Tab 右键菜单 / 重命名 / 删除 / 拖拽排序 ---

    def _sc_qc_on_project_tab_context_menu(self, pos):
        tabs = self._sc_qc_project_tabs
        index = tabs.tabAt(pos)
        if index < 0:
            return
        project_id = tabs.tabData(index)
        if not project_id or project_id == self._SC_QC_ADD_TAB_MARK:
            return
        project = self._sc_qc_get_project(project_id)
        if project is None:
            return
        menu = QMenu(self)
        act_rename = menu.addAction("重命名")
        act_export = menu.addAction("导出")
        menu.addSeparator()
        act_delete = menu.addAction("删除")
        # 仅剩一个项目时禁止删除，防止数据完全清空
        if len(self._sc_qc_data.get("projects", [])) <= 1:
            act_delete.setEnabled(False)
        chosen = menu.exec(tabs.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is act_rename:
            self._sc_qc_rename_project(project)
        elif chosen is act_export:
            self._sc_qc_export_project(project)
        elif chosen is act_delete:
            self._sc_qc_delete_project(project)

    def _sc_qc_rename_project(self, project):
        if not isinstance(project, dict):
            return
        old_name = project.get("name", "")
        text, ok = QInputDialog.getText(
            self, "重命名项目", "项目名称:", QLineEdit.Normal, old_name
        )
        if not ok:
            return
        new_name = text.strip()
        if not new_name or new_name == old_name:
            return
        project["name"] = new_name
        self._sc_qc_save_data()
        self._sc_qc_refresh_project_tabs()

    def _sc_qc_delete_project(self, project):
        if not isinstance(project, dict):
            return
        projects = self._sc_qc_data.get("projects", [])
        if len(projects) <= 1:
            QMessageBox.warning(self, "提示", "至少需要保留一个项目")
            return
        ret = QMessageBox.question(
            self, "删除项目",
            f"确定删除项目「{project.get('name', '')}」及其全部分组与指令？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        try:
            projects.remove(project)
        except ValueError:
            return
        # 若删的是当前项目，回退到第一个
        if self._sc_qc_data.get("last_project_id") == project.get("id"):
            first = projects[0]
            self._sc_qc_data["last_project_id"] = first.get("id", "")
            groups = first.get("groups", [])
            self._sc_qc_data["last_group_id"] = groups[0].get("id", "") if groups else ""
        self._sc_qc_save_data()
        self._sc_qc_refresh_all()

    def _sc_qc_on_project_reorder(self, source_index: int, target_index: int):
        projects = self._sc_qc_data.get("projects", [])
        n = len(projects)
        if n <= 1:
            return
        if source_index < 0 or source_index >= n:
            return
        # 钳制目标到合法范围（拖到 "+" tab 等价于挪到末尾）
        if target_index < 0:
            target_index = 0
        if target_index >= n:
            target_index = n - 1
        if source_index == target_index:
            return
        item = projects.pop(source_index)
        projects.insert(target_index, item)
        self._sc_qc_save_data()
        self._sc_qc_refresh_project_tabs()

    # --- 新增 ---

    def _sc_qc_prompt_text(self, title: str, label: str) -> str:
        text, ok = QInputDialog.getText(self, title, label)
        if not ok:
            return ""
        return text.strip()

    def _sc_qc_add_project(self) -> bool:
        name = self._sc_qc_prompt_text("新增项目", "项目名称:")
        if not name:
            return False
        project = {
            "id": self._sc_qc_gen_id("project"),
            "name": name,
            "groups": [
                {
                    "id": self._sc_qc_gen_id("group"),
                    "name": "默认分组",
                    "commands": [],
                }
            ],
        }
        self._sc_qc_data.setdefault("projects", []).append(project)
        self._sc_qc_data["last_project_id"] = project["id"]
        self._sc_qc_data["last_group_id"] = project["groups"][0]["id"]
        self._sc_qc_save_data()
        self._sc_qc_refresh_all()
        return True

    def _sc_qc_add_group(self):
        project = self._sc_qc_current_project()
        if project is None:
            QMessageBox.warning(self, "提示", "请先创建项目")
            return
        name = self._sc_qc_prompt_text("新增分组", "分组名称:")
        if not name:
            return
        group = {
            "id": self._sc_qc_gen_id("group"),
            "name": name,
            "commands": [],
        }
        project.setdefault("groups", []).append(group)
        self._sc_qc_data["last_group_id"] = group["id"]
        self._sc_qc_save_data()
        self._sc_qc_refresh_group_combo()
        self._sc_refresh_quick_buttons()

    # --- 分组右键菜单 / 重命名 / 删除 ---

    def _sc_qc_on_group_combo_context_menu(self, pos):
        combo = self._sc_qc_group_combo
        # 优先取右键位置下的项；取不到时退回当前项
        index = combo.view().indexAt(combo.view().mapFrom(combo, pos)).row()
        if index < 0:
            index = combo.currentIndex()
        if index < 0:
            return
        group_id = combo.itemData(index)
        if not group_id:
            return
        project = self._sc_qc_current_project()
        group = self._sc_qc_get_group(project, group_id)
        if group is None:
            return
        menu = QMenu(self)
        act_rename = menu.addAction("重命名")
        menu.addSeparator()
        act_delete = menu.addAction("删除")
        # 仅剩一个分组时禁止删除，防止当前项目分组完全清空
        if len(project.get("groups", [])) <= 1:
            act_delete.setEnabled(False)
        chosen = menu.exec(combo.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen is act_rename:
            self._sc_qc_rename_group(group)
        elif chosen is act_delete:
            self._sc_qc_delete_group(group)

    def _sc_qc_rename_group(self, group):
        if not isinstance(group, dict):
            return
        old_name = group.get("name", "")
        text, ok = QInputDialog.getText(
            self, "重命名分组", "分组名称:", QLineEdit.Normal, old_name
        )
        if not ok:
            return
        new_name = text.strip()
        if not new_name or new_name == old_name:
            return
        group["name"] = new_name
        self._sc_qc_save_data()
        self._sc_qc_refresh_group_combo()

    def _sc_qc_delete_group(self, group):
        if not isinstance(group, dict):
            return
        project = self._sc_qc_current_project()
        if project is None:
            return
        groups = project.get("groups", [])
        if len(groups) <= 1:
            QMessageBox.warning(self, "提示", "至少需要保留一个分组")
            return
        ret = QMessageBox.question(
            self, "删除分组",
            f"确定删除分组「{group.get('name', '')}」及其全部指令？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        try:
            groups.remove(group)
        except ValueError:
            return
        # 若删的是当前分组，回退到第一个
        if self._sc_qc_data.get("last_group_id") == group.get("id"):
            self._sc_qc_data["last_group_id"] = groups[0].get("id", "") if groups else ""
        self._sc_qc_save_data()
        self._sc_qc_refresh_group_combo()
        self._sc_refresh_quick_buttons()

    def _sc_add_quick_cmd(self):
        group = self._sc_qc_current_group()
        if group is None:
            QMessageBox.warning(self, "提示", "请先创建项目和分组")
            return
        prefill_cmd = self._sc_send_input.text().strip()
        dlg = _QuickCmdDialog(parent=self, content=prefill_cmd)
        if dlg.exec() != QDialog.Accepted:
            return
        cmd = dlg.get_command()
        if not cmd or not cmd.get("content"):
            return
        cmd["id"] = self._sc_qc_gen_id("cmd")
        group.setdefault("commands", []).append(cmd)
        self._sc_qc_save_data()
        self._sc_refresh_quick_buttons()

    # --- 快捷指令按钮：右键菜单（编辑 / 删除） ---

    def _sc_qc_on_cmd_btn_context_menu(self, btn, pos, idx):
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        if not (0 <= idx < len(commands)):
            return
        menu = QMenu(self)
        act_edit = menu.addAction("编辑指令")
        act_del = menu.addAction("删除指令")
        act = menu.exec(btn.mapToGlobal(pos))
        if act is None:
            return
        if act == act_edit:
            self._sc_qc_edit_command(idx)
        elif act == act_del:
            self._sc_qc_delete_command(idx)

    def _sc_qc_edit_command(self, idx):
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        if not (0 <= idx < len(commands)):
            return
        entry = commands[idx]
        dlg = _QuickCmdDialog(
            parent=self,
            name=entry.get("name", ""),
            content=entry.get("content", ""),
            send_type=entry.get("send_type", "text"),
            line_ending=entry.get("line_ending", "\r\n"),
            encoding=entry.get("encoding", "ascii"),
        )
        if dlg.exec() != QDialog.Accepted:
            return
        new_cmd = dlg.get_command()
        if not new_cmd or not new_cmd.get("content"):
            return
        # 保留原 id，覆盖其它字段
        new_cmd["id"] = entry.get("id") or self._sc_qc_gen_id("cmd")
        commands[idx] = new_cmd
        self._sc_qc_save_data()
        self._sc_refresh_quick_buttons()

    def _sc_qc_delete_command(self, idx):
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        if not (0 <= idx < len(commands)):
            return
        entry = commands[idx]
        name = entry.get("name", "") or entry.get("content", "")
        ret = QMessageBox.question(
            self,
            "删除指令",
            f"确定要删除指令 \"{name}\" 吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return
        commands.pop(idx)
        self._sc_qc_save_data()
        self._sc_refresh_quick_buttons()

    def _sc_qc_reorder_command(self, source_idx, target_idx):
        group = self._sc_qc_current_group()
        if group is None:
            return
        commands = group.get("commands", []) or []
        n = len(commands)
        if not (0 <= source_idx < n):
            return
        # 目标越界则视为追加到末尾
        if target_idx < 0 or target_idx >= n:
            target_idx = n - 1
        if source_idx == target_idx:
            return
        item = commands.pop(source_idx)
        commands.insert(target_idx, item)
        self._sc_qc_save_data()
        self._sc_refresh_quick_buttons()

    # --- 快捷指令按钮：拖拽排序（容器层 eventFilter） ---

    def eventFilter(self, obj, event):
        # 仅处理快捷指令容器上的拖拽事件；其它一律放行
        container = getattr(self, "_sc_qc_btn_container", None)
        if container is not None and obj is container:
            etype = event.type()
            from PySide6.QtCore import QEvent  # 局部引入，避免顶部冗余导入
            if etype == QEvent.DragEnter:
                if event.mimeData().hasFormat(_QuickCmdButton._MIME_TYPE):
                    event.acceptProposedAction()
                    return True
            elif etype == QEvent.DragMove:
                if event.mimeData().hasFormat(_QuickCmdButton._MIME_TYPE):
                    event.acceptProposedAction()
                    return True
            elif etype == QEvent.Drop:
                if event.mimeData().hasFormat(_QuickCmdButton._MIME_TYPE):
                    try:
                        source_idx = int(
                            bytes(event.mimeData().data(
                                _QuickCmdButton._MIME_TYPE
                            )).decode()
                        )
                    except (ValueError, UnicodeDecodeError):
                        return False
                    # 命中目标按钮：从落点反查最近的 _QuickCmdButton
                    pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
                    target_idx = self._sc_qc_locate_drop_index(pos, source_idx)
                    event.acceptProposedAction()
                    self._sc_qc_reorder_command(source_idx, target_idx)
                    return True
        return super().eventFilter(obj, event)

    def _sc_qc_locate_drop_index(self, pos, source_idx):
        """根据落点定位目标插入索引：命中按钮取其 command_index；
        否则按 grid 行列估算最近按钮；都不命中则返回末尾。
        """
        container = self._sc_qc_btn_container
        commands = (
            self._sc_qc_current_group() or {}
        ).get("commands", []) or []
        n = len(commands)
        if n == 0:
            return 0
        # 1) 直接命中：containerAt -> 反查 _QuickCmdButton
        child = container.childAt(pos)
        while child is not None and not isinstance(child, _QuickCmdButton):
            child = child.parentWidget()
            if child is container:
                child = None
                break
        if isinstance(child, _QuickCmdButton):
            ti = child.command_index()
            if 0 <= ti < n:
                return ti
        # 2) 未命中按钮：按 y 取最近一行的最后一个按钮所在索引
        layout = self._sc_qc_btn_layout
        nearest_idx = n - 1
        nearest_dy = None
        for i in range(layout.count()):
            item = layout.itemAt(i)
            w = item.widget() if item is not None else None
            if not isinstance(w, _QuickCmdButton):
                continue
            geo = w.geometry()
            if geo.top() <= pos.y() <= geo.bottom():
                # 同一行：取该行内 x 最接近的按钮
                if pos.x() <= geo.center().x():
                    return w.command_index()
                # 大于中心：插到该按钮之后（下一项的位置）
                ci = w.command_index()
                return min(ci + 1 if ci + 1 < n else ci, n - 1)
            dy = abs(geo.center().y() - pos.y())
            if nearest_dy is None or dy < nearest_dy:
                nearest_dy = dy
                nearest_idx = w.command_index()
        return nearest_idx

    # --- 发送 ---

    def _sc_send_quick(self, entry):
        if not isinstance(entry, dict):
            return
        content = entry.get("content", "")
        send_type = entry.get("send_type", "text")
        line_ending = entry.get("line_ending", "")
        encoding = entry.get("encoding", "ascii") or "ascii"

        if send_type == "hex":
            try:
                data = bytes.fromhex(content.replace(" ", ""))
            except ValueError:
                self._sc_append_system(f"[ERROR] Invalid HEX: {content}")
                return
        else:
            text = content + (line_ending or "")
            try:
                data = text.encode(encoding)
            except (UnicodeEncodeError, LookupError) as e:
                self._sc_append_system(f"[ERROR] Encode failed ({encoding}): {e}")
                return

        ok = self.serial_send(data)
        if ok:
            self._sc_tx_bytes += len(data)
            self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))
            if self._sc_show_send:
                display = data.hex(' ') if send_type == "hex" else content
                self._sc_append_log(f"[TX] {display}", _CLR_TX)
        else:
            self._sc_append_system("[ERROR] Send failed, serial not connected")

    # --- 导入 / 导出 ---

    def _sc_qc_collect_existing_ids(self):
        ids = set()
        for p in self._sc_qc_data.get("projects", []):
            ids.add(p.get("id", ""))
            for g in p.get("groups", []):
                ids.add(g.get("id", ""))
                for c in g.get("commands", []):
                    ids.add(c.get("id", ""))
        ids.discard("")
        return ids

    @staticmethod
    def _sc_qc_unique_cmd_name(base: str, used_names: set) -> str:
        if base not in used_names:
            return base
        candidate = f"{base}_导入"
        if candidate not in used_names:
            return candidate
        i = 1
        while True:
            candidate = f"{base}_导入_{i}"
            if candidate not in used_names:
                return candidate
            i += 1

    def _sc_import_quick_cmds(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Quick Commands", "", "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            QMessageBox.critical(self, "导入失败", f"无法读取文件:\n{e}")
            return

        if not isinstance(data, dict):
            QMessageBox.critical(self, "导入失败", "JSON 格式不符合要求")
            return

        qc_payload = None
        if "quick_commands" in data and isinstance(data["quick_commands"], dict):
            qc_payload = data["quick_commands"]
        elif "projects" in data and isinstance(data["projects"], list):
            qc_payload = data
        else:
            QMessageBox.critical(self, "导入失败", "JSON 格式不符合要求 (需包含 quick_commands 或 projects)")
            return

        if not isinstance(qc_payload.get("projects"), list):
            QMessageBox.critical(self, "导入失败", "JSON 格式不符合要求 (需包含 projects 列表)")
            return

        self._sc_merge_quick_cmds(qc_payload)

    def _sc_merge_quick_cmds(self, data: dict):
        used_ids = self._sc_qc_collect_existing_ids()
        stat = {"project": 0, "group": 0, "cmd": 0, "renamed": 0}

        def fix_id(prefix, raw_id):
            if raw_id and raw_id not in used_ids:
                used_ids.add(raw_id)
                return raw_id
            new_id = self._sc_qc_gen_id(prefix)
            while new_id in used_ids:
                new_id = self._sc_qc_gen_id(prefix)
            used_ids.add(new_id)
            return new_id

        def iter_groups(ip):
            if isinstance(ip.get("regions"), list):
                for ir in ip.get("regions", []) or []:
                    if not isinstance(ir, dict):
                        continue
                    for ig in ir.get("groups", []) or []:
                        if isinstance(ig, dict):
                            yield ig
            for ig in ip.get("groups", []) or []:
                if isinstance(ig, dict):
                    yield ig

        existing_projects = self._sc_qc_data.setdefault("projects", [])
        for ip in data["projects"]:
            if not isinstance(ip, dict):
                continue
            pname = ip.get("name", "未命名项目")
            target_p = next((p for p in existing_projects if p.get("name") == pname), None)
            if target_p is None:
                target_p = {
                    "id": fix_id("project", ip.get("id", "")),
                    "name": pname,
                    "groups": [],
                }
                existing_projects.append(target_p)
                stat["project"] += 1

            for ig in iter_groups(ip):
                gname = ig.get("name", "未命名分组")
                target_g = next(
                    (g for g in target_p.setdefault("groups", []) if g.get("name") == gname),
                    None,
                )
                if target_g is None:
                    target_g = {
                        "id": fix_id("group", ig.get("id", "")),
                        "name": gname,
                        "commands": [],
                    }
                    target_p["groups"].append(target_g)
                    stat["group"] += 1

                existing_contents = {
                    (c.get("name", ""), c.get("content", ""))
                    for c in target_g.setdefault("commands", [])
                }
                used_names = {c.get("name", "") for c in target_g["commands"]}
                for ic in ig.get("commands", []) or []:
                    if not isinstance(ic, dict):
                        continue
                    ic_name = ic.get("name", "") or "未命名指令"
                    ic_content = ic.get("content", "")
                    if (ic_name, ic_content) in existing_contents:
                        continue
                    new_name = self._sc_qc_unique_cmd_name(ic_name, used_names)
                    if new_name != ic_name:
                        stat["renamed"] += 1
                    new_cmd = {
                        "id": fix_id("cmd", ic.get("id", "")),
                        "name": new_name,
                        "content": ic_content,
                        "send_type": ic.get("send_type", "text"),
                        "line_ending": ic.get("line_ending", ""),
                        "encoding": ic.get("encoding", "ascii"),
                    }
                    target_g["commands"].append(new_cmd)
                    used_names.add(new_name)
                    existing_contents.add((new_name, ic_content))
                    stat["cmd"] += 1

        self._sc_qc_save_data()
        self._sc_qc_refresh_all()
        QMessageBox.information(
            self, "导入完成",
            f"增量合入完成\n新增项目:{stat['project']}\n"
            f"新增分组:{stat['group']}\n新增指令:{stat['cmd']}\n重命名指令:{stat['renamed']}\n"
            f"(已跳过名称和内容完全相同的重复指令)",
        )

    def _sc_export_quick_cmds(self):
        project = self._sc_qc_current_project()
        if project is None:
            QMessageBox.warning(self, "提示", "当前没有可导出的项目")
            return
        self._sc_qc_export_project(project)

    def _sc_qc_export_project(self, project):
        if not isinstance(project, dict):
            return
        default_name = f"{project.get('name', 'project')}_快捷指令.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Quick Commands", default_name, "JSON Files (*.json);;All Files (*)"
        )
        if not path:
            return
        payload = {
            "version": "2.0",
            "quick_commands": {
                "version": "1.0",
                "projects": [
                    {
                        "id": project.get("id", ""),
                        "name": project.get("name", ""),
                        "groups": project.get("groups", []),
                    }
                ],
            },
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            self._sc_append_system(f"[INFO] Exported project: {project.get('name', '')}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"写入失败:\n{e}")

    # --- persistence (unified config: KK_SerialConsole.json) ---
    #
    # 设计目标:
    #   - 所有串口工具配置（串口参数 / UI偏好 / 快捷指令）统一保存到单文件 KK_SerialConsole.json
    #   - 模块可能被**单独编译**分发, 因此用户目录不挂在 KK_Lab 应用名下,
    #     而是使用独立的 "SerialCom" 命名空间:
    #       打包态: %APPDATA%\SerialCom\
    #       开发态: <项目根>/user_data/SerialCom/
    #   - 严禁写到 EXE 同目录或 sys._MEIPASS, 兼容 Program Files / onefile 临时目录
    #   - 启动时自动加载, 优先顺序:
    #       1) 用户目录 (%APPDATA%\SerialCom\  /  user_data/SerialCom/)
    #       2) 回退: EXE 同目录 (打包态) / <项目根>/Results/ (开发态)
    #     回退来源仅做**只读**加载, 不会反写到用户目录, 避免污染系统配置.
    #   - 应用退出时由调用方触发 _sc_save_persisted_state()

    _SC_UNIFIED_FILENAME = "KK_SerialConsole.json"
    _SC_APP_NAMESPACE = "SerialCom"

    def _sc_user_config_dir(self) -> str:
        if getattr(_sys, "frozen", False):
            base = _os.environ.get("APPDATA")
            if not base:
                base = _os.path.join(_os.path.expanduser("~"), "AppData", "Roaming")
            root = _os.path.join(base, self._SC_APP_NAMESPACE)
        else:
            root = _os.path.join(_PROJECT_ROOT, "user_data", self._SC_APP_NAMESPACE)
        try:
            _os.makedirs(root, exist_ok=True)
        except OSError:
            pass
        return root

    def _sc_persisted_path(self) -> str:
        return os.path.join(self._sc_user_config_dir(), self._SC_UNIFIED_FILENAME)

    def _sc_fallback_dir(self) -> str:
        if getattr(_sys, "frozen", False):
            return _os.path.dirname(_sys.executable)
        return _os.path.join(_PROJECT_ROOT, "Results")

    def _sc_fallback_path(self) -> str:
        return os.path.join(self._sc_fallback_dir(), self._SC_UNIFIED_FILENAME)

    def _sc_migrate_legacy_config(self):
        base = self._sc_user_config_dir()
        legacy_cfg = os.path.join(base, "config.json")
        legacy_qc = os.path.join(base, "quick_commands.json")
        migrated = False

        if os.path.isfile(legacy_cfg):
            try:
                with open(legacy_cfg, "r", encoding="utf-8") as f:
                    self._sc_apply_persisted_state(json.load(f))
                migrated = True
            except Exception:
                pass

        if os.path.isfile(legacy_qc):
            try:
                with open(legacy_qc, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                parsed = self._sc_parse_quick_cmds_payload(raw)
                if parsed is not None:
                    self._sc_qc_data = parsed
                    migrated = True
            except Exception:
                pass

        if not migrated:
            fb_dir = self._sc_fallback_dir()
            fb_cfg = os.path.join(fb_dir, "config.json")
            fb_qc = os.path.join(fb_dir, "quick_commands.json")
            if os.path.isfile(fb_cfg):
                try:
                    with open(fb_cfg, "r", encoding="utf-8") as f:
                        self._sc_apply_persisted_state(json.load(f))
                except Exception:
                    pass
            if os.path.isfile(fb_qc):
                try:
                    with open(fb_qc, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                    parsed = self._sc_parse_quick_cmds_payload(raw)
                    if parsed is not None:
                        self._sc_qc_data = parsed
                except Exception:
                    pass

    def _sc_parse_quick_cmds_payload(self, data):
        """校验并标准化快捷指令 JSON; 不符合新格式返回 None."""
        if not isinstance(data, dict):
            return None
        if "projects" not in data or not isinstance(data["projects"], list):
            return None
        normalized = {
            "version": str(data.get("version", "1.0")),
            "last_project_id": str(data.get("last_project_id", "")),
            "last_group_id": str(data.get("last_group_id", "")),
            "projects": [],
        }
        for p in data["projects"]:
            if not isinstance(p, dict):
                continue
            np = {
                "id": str(p.get("id") or self._sc_qc_gen_id("project")),
                "name": str(p.get("name", "未命名项目")),
                "groups": [],
            }

            def _norm_group(g):
                ng = {
                    "id": str(g.get("id") or self._sc_qc_gen_id("group")),
                    "name": str(g.get("name", "未命名分组")),
                    "commands": [],
                }
                for c in g.get("commands", []) or []:
                    if not isinstance(c, dict):
                        continue
                    ng["commands"].append({
                        "id": str(c.get("id") or self._sc_qc_gen_id("cmd")),
                        "name": str(c.get("name", "")),
                        "content": str(c.get("content", "")),
                        "send_type": str(c.get("send_type", "text")),
                        "line_ending": str(c.get("line_ending", "")),
                        "encoding": str(c.get("encoding", "ascii")),
                    })
                return ng

            # 兼容旧格式：projects[].regions[].groups[] -> 拍平为 groups[]，分组重名加 _合并 后缀
            used_names = set()

            def _uniq_name(base):
                if base not in used_names:
                    used_names.add(base)
                    return base
                cand = f"{base}_合并"
                idx = 1
                while cand in used_names:
                    cand = f"{base}_合并_{idx}"
                    idx += 1
                used_names.add(cand)
                return cand

            if isinstance(p.get("regions"), list):
                for r in p.get("regions", []) or []:
                    if not isinstance(r, dict):
                        continue
                    for g in r.get("groups", []) or []:
                        if not isinstance(g, dict):
                            continue
                        ng = _norm_group(g)
                        ng["name"] = _uniq_name(ng["name"])
                        np["groups"].append(ng)
            for g in p.get("groups", []) or []:
                if not isinstance(g, dict):
                    continue
                ng = _norm_group(g)
                ng["name"] = _uniq_name(ng["name"])
                np["groups"].append(ng)
            normalized["projects"].append(np)
        return normalized

    def _sc_collect_persisted_state(self) -> dict:
        port_text = ""
        if hasattr(self, "_sc_port_combo"):
            port_text = self._sc_port_combo.currentText()
        baud_text = "921600"
        if hasattr(self, "_sc_baud_combo"):
            baud_text = self._sc_baud_combo.currentText()
        auto_detect = False
        if hasattr(self, "_sc_auto_detect_cb"):
            auto_detect = self._sc_auto_detect_cb.isChecked()
        databit = "8"
        if hasattr(self, "_sc_databit_combo"):
            databit = self._sc_databit_combo.currentText()
        stopbit = "1"
        if hasattr(self, "_sc_stopbit_combo"):
            stopbit = self._sc_stopbit_combo.currentText()
        parity = "None"
        if hasattr(self, "_sc_parity_combo"):
            parity = self._sc_parity_combo.currentText()
        flow_ctrl = "None"
        if hasattr(self, "_sc_flow_combo"):
            flow_ctrl = self._sc_flow_combo.currentText()

        auto_detect_config = {}
        if hasattr(self, "_sc_auto_baud_monitor"):
            m = self._sc_auto_baud_monitor
            auto_detect_config = {
                "runtime_redetect_enabled": m.runtime_redetect_enabled,
                "candidate_baudrates": list(m._config.get("candidate_baudrates", [])),
                "lock_threshold": m._config.get("lock_threshold", 85),
                "bad_threshold": m._config.get("bad_threshold", 40),
                "bad_windows_to_suspect": m._config.get("bad_windows_to_suspect", 3),
                "suspect_windows_to_scan": m._config.get("suspect_windows_to_scan", 2),
                "monitor_window_max_time_ms": m._config.get("monitor_window_max_time_ms", 500),
                "switch_cooldown_ms": m._config.get("switch_cooldown_ms", 5000),
                "switch_score_margin": m._config.get("switch_score_margin", 15),
                "confirm_scan_rounds": m._config.get("confirm_scan_rounds", 2),
            }

        return {
            "version": "2.0",
            "serial": {
                "port": port_text,
                "baudrate": baud_text,
                "auto_detect": auto_detect,
                "databits": databit,
                "stopbits": stopbit,
                "parity": parity,
                "flow_control": flow_ctrl,
                "auto_detect_config": auto_detect_config,
            },
            "ui": {
                "rx_display_hex": getattr(self, "_sc_rx_display_hex", False),
                "tx_display_hex": getattr(self, "_sc_tx_display_hex", False),
                "show_timestamp": getattr(self, "_sc_show_timestamp", True),
                "auto_resend": getattr(self, "_sc_auto_resend", False),
                "resend_interval": getattr(self, "_sc_resend_interval", 1000),
                "line_ending": getattr(self, "_sc_line_ending", "\r\n"),
                "show_send": getattr(self, "_sc_show_send", True),
                "line_by_line": getattr(self, "_sc_line_by_line", False),
                "sidebar_visible": getattr(self, "_sc_sidebar_visible", True),
            },
            "send_history": list(getattr(self, "_sc_send_history", []))[-50:],
            "quick_commands": getattr(self, "_sc_qc_data", self._sc_qc_default_data()),
        }

    def _sc_apply_persisted_state(self, data: dict) -> None:
        if not isinstance(data, dict):
            return

        is_v2 = data.get("version") == "2.0" or "serial" in data

        if is_v2:
            serial_cfg = data.get("serial", {})
            if isinstance(serial_cfg, dict):
                port = serial_cfg.get("port", "")
                if port and hasattr(self, "_sc_port_combo"):
                    idx = self._sc_port_combo.findText(port)
                    if idx >= 0:
                        self._sc_port_combo.setCurrentIndex(idx)
                    else:
                        self._sc_last_port = port

                baud = serial_cfg.get("baudrate", "")
                if baud and hasattr(self, "_sc_baud_combo"):
                    idx = self._sc_baud_combo.findText(str(baud))
                    if idx >= 0:
                        self._sc_baud_combo.setCurrentIndex(idx)
                    else:
                        self._sc_baud_combo.setCurrentText(str(baud))

                if hasattr(self, "_sc_auto_detect_cb"):
                    self._sc_auto_detect_cb.setChecked(bool(serial_cfg.get("auto_detect", False)))

                if hasattr(self, "_sc_databit_combo"):
                    db = serial_cfg.get("databits", "8")
                    idx = self._sc_databit_combo.findText(str(db))
                    if idx >= 0:
                        self._sc_databit_combo.setCurrentIndex(idx)

                if hasattr(self, "_sc_stopbit_combo"):
                    sb = serial_cfg.get("stopbits", "1")
                    idx = self._sc_stopbit_combo.findText(str(sb))
                    if idx >= 0:
                        self._sc_stopbit_combo.setCurrentIndex(idx)

                if hasattr(self, "_sc_parity_combo"):
                    pa = serial_cfg.get("parity", "None")
                    idx = self._sc_parity_combo.findText(str(pa))
                    if idx >= 0:
                        self._sc_parity_combo.setCurrentIndex(idx)

                if hasattr(self, "_sc_flow_combo"):
                    fc = serial_cfg.get("flow_control", "None")
                    idx = self._sc_flow_combo.findText(str(fc))
                    if idx >= 0:
                        self._sc_flow_combo.setCurrentIndex(idx)

                ad_cfg = serial_cfg.get("auto_detect_config", {})
                if isinstance(ad_cfg, dict) and hasattr(self, "_sc_auto_baud_monitor"):
                    m = self._sc_auto_baud_monitor
                    if "runtime_redetect_enabled" in ad_cfg:
                        m.runtime_redetect_enabled = bool(ad_cfg["runtime_redetect_enabled"])
                    for k in ("candidate_baudrates", "lock_threshold", "bad_threshold",
                              "bad_windows_to_suspect", "suspect_windows_to_scan",
                              "monitor_window_max_time_ms", "switch_cooldown_ms",
                              "switch_score_margin", "confirm_scan_rounds"):
                        if k in ad_cfg:
                            m._config[k] = ad_cfg[k]

            ui_cfg = data.get("ui", {})
            if isinstance(ui_cfg, dict):
                for key, attr in (
                    ("rx_display_hex", "_sc_rx_display_hex"),
                    ("tx_display_hex", "_sc_tx_display_hex"),
                    ("show_timestamp", "_sc_show_timestamp"),
                    ("auto_resend", "_sc_auto_resend"),
                    ("resend_interval", "_sc_resend_interval"),
                    ("line_ending", "_sc_line_ending"),
                    ("show_send", "_sc_show_send"),
                    ("line_by_line", "_sc_line_by_line"),
                    ("sidebar_visible", "_sc_sidebar_visible"),
                ):
                    if key in ui_cfg:
                        setattr(self, attr, ui_cfg[key])

            if isinstance(data.get("send_history"), list):
                self._sc_send_history = [str(x) for x in data["send_history"]]
                if hasattr(self, "_sc_history_combo"):
                    self._sc_history_combo.blockSignals(True)
                    self._sc_history_combo.clear()
                    self._sc_history_combo.addItems(self._sc_send_history)
                    self._sc_history_combo.setCurrentIndex(-1)
                    self._sc_history_combo.blockSignals(False)

            qc = data.get("quick_commands")
            if isinstance(qc, dict):
                parsed = self._sc_parse_quick_cmds_payload(qc)
                if parsed is not None:
                    self._sc_qc_data = parsed
        else:
            for key, attr in (
                ("rx_display_hex", "_sc_rx_display_hex"),
                ("tx_display_hex", "_sc_tx_display_hex"),
                ("show_timestamp", "_sc_show_timestamp"),
                ("auto_resend", "_sc_auto_resend"),
                ("resend_interval", "_sc_resend_interval"),
                ("line_ending", "_sc_line_ending"),
                ("show_send", "_sc_show_send"),
                ("line_by_line", "_sc_line_by_line"),
                ("sidebar_visible", "_sc_sidebar_visible"),
            ):
                if key in data:
                    setattr(self, attr, data[key])
            if isinstance(data.get("send_history"), list):
                self._sc_send_history = [str(x) for x in data["send_history"]]
                if hasattr(self, "_sc_history_combo"):
                    self._sc_history_combo.blockSignals(True)
                    self._sc_history_combo.clear()
                    self._sc_history_combo.addItems(self._sc_send_history)
                    self._sc_history_combo.setCurrentIndex(-1)
                    self._sc_history_combo.blockSignals(False)

    def _sc_load_persisted_state(self) -> None:
        try:
            cfg_path = self._sc_persisted_path()
            fb_path = self._sc_fallback_path()

            source = None
            if os.path.isfile(cfg_path):
                source = cfg_path
            elif os.path.isfile(fb_path) and os.path.abspath(fb_path) != os.path.abspath(cfg_path):
                source = fb_path

            if source:
                load_err = None
                raw = None
                try:
                    with open(source, "r", encoding="utf-8") as f:
                        raw = json.load(f)
                except Exception as e:
                    load_err = e

                if load_err is not None:
                    try:
                        QMessageBox.warning(
                            self, "配置文件损坏",
                            f"无法解析 {source}:\n{load_err}\n\n已恢复为默认配置。",
                        )
                    except Exception:
                        pass
                    self._sc_qc_data = self._sc_qc_default_data()
                    if hasattr(self, "_sc_append_system"):
                        self._sc_append_system(f"[WARN] Config corrupted, using defaults. Path: {source}")
                elif not isinstance(raw, dict):
                    self._sc_qc_data = self._sc_qc_default_data()
                    if hasattr(self, "_sc_append_system"):
                        self._sc_append_system(f"[WARN] Config invalid format, using defaults. Path: {source}")
                else:
                    self._sc_apply_persisted_state(raw)
                    if not hasattr(self, "_sc_qc_data") or not self._sc_qc_data:
                        self._sc_qc_data = self._sc_qc_default_data()

                    if hasattr(self, "_sc_append_system"):
                        try:
                            origin = "user" if source == cfg_path else "fallback"
                            total = sum(
                                len(g.get("commands", []))
                                for p in self._sc_qc_data.get("projects", [])
                                for g in p.get("groups", [])
                            )
                            self._sc_append_system(
                                f"[INFO] Loaded config from {origin}: {source} ({total} quick commands)"
                            )
                        except Exception:
                            pass
            else:
                self._sc_migrate_legacy_config()
                if not hasattr(self, "_sc_qc_data") or not self._sc_qc_data:
                    self._sc_qc_data = self._sc_qc_default_data()
                try:
                    self._sc_save_persisted_state()
                except Exception:
                    pass
                if hasattr(self, "_sc_append_system"):
                    self._sc_append_system(f"[INFO] Config path: {cfg_path}")

            try:
                self._sc_qc_refresh_all()
            except Exception:
                pass
        except Exception:
            pass

    def _sc_save_persisted_state(self) -> None:
        try:
            cfg_path = self._sc_persisted_path()
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(self._sc_collect_persisted_state(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _sc_qc_save_data(self) -> None:
        self._sc_save_persisted_state()

    # --- log helpers ---

    _SC_MAX_LOG_LINES = 10000

    def _sc_append_log(self, message: str, color: str = _CLR_TEXT_BODY):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3] if self._sc_show_timestamp else ""
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ts_html = f'<span style="color:{_CLR_TEXT_TIME};">{ts}</span> ' if ts else ""
        html = f'{ts_html}<span style="color:{color};">{escaped}</span>'
        self._sc_all_logs.append((message, html))
        if len(self._sc_all_logs) > self._SC_MAX_LOG_LINES:
            self._sc_all_logs = self._sc_all_logs[-self._SC_MAX_LOG_LINES:]
        if self._sc_is_filter_active():
            self._sc_filter_dirty = True
        else:
            self._sc_pending_html.append(html)

    def _sc_flush_pending_logs(self):
        if self._sc_is_filter_active():
            if getattr(self, '_sc_filter_dirty', False):
                self._sc_filter_dirty = False
                before = self._sc_filter_applied_before
                after = self._sc_filter_applied_after
                if before == 0 and after == 0:
                    self._sc_flush_filter_incremental()
                else:
                    self._sc_apply_filter()
        elif self._sc_pending_html:
            batch = self._sc_pending_html[:200]
            self._sc_pending_html = self._sc_pending_html[200:]
            self._sc_log_edit.setUpdatesEnabled(False)
            cursor = self._sc_log_edit.textCursor()
            cursor.beginEditBlock()
            for html in batch:
                self._sc_log_edit.append(html)
            cursor.endEditBlock()
            self._sc_log_edit.setUpdatesEnabled(True)
            if self._sc_auto_scroll:
                self._sc_scroll_to_bottom()
        self._sc_flush_extra_panels()

    def _sc_flush_filter_incremental(self):
        pattern = self._sc_filter_applied_pattern
        if not pattern:
            return
        use_regex = self._sc_filter_applied_use_regex
        case_sensitive = self._sc_filter_applied_case
        invert = self._sc_filter_applied_invert

        compiled = None
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                compiled = re.compile(pattern, flags)
            except re.error:
                return

        start_idx = self._sc_filter_last_count
        new_html = []
        new_match_count = 0

        for i in range(start_idx, len(self._sc_all_logs)):
            raw = self._sc_all_logs[i][0]
            if compiled is not None:
                hit = bool(compiled.search(raw))
            elif case_sensitive:
                hit = pattern in raw
            else:
                hit = pattern.lower() in raw.lower()
            if invert:
                hit = not hit
            if hit:
                new_match_count += 1
                base_html = self._sc_all_logs[i][1]
                if not invert:
                    base_html = self._sc_html_with_filter_highlight(
                        base_html, pattern, use_regex, case_sensitive
                    )
                new_html.append(base_html)

        self._sc_filter_last_count = len(self._sc_all_logs)
        prev_text = self._sc_filter_match_label.text()
        prev_count = 0
        if prev_text.startswith("Matched: "):
            try:
                prev_count = int(prev_text.split(":")[1].strip().split()[0])
            except (ValueError, IndexError):
                pass
        total_match = prev_count + new_match_count
        self._sc_filter_match_label.setText(f"Matched: {total_match} lines")

        if new_html:
            self._sc_log_edit.setUpdatesEnabled(False)
            cursor = self._sc_log_edit.textCursor()
            cursor.beginEditBlock()
            for html in new_html:
                self._sc_log_edit.append(html)
            cursor.endEditBlock()
            self._sc_log_edit.setUpdatesEnabled(True)
            if self._sc_auto_scroll:
                self._sc_scroll_to_bottom()

    def _sc_append_system(self, message: str):
        color_map = {"INFO": _CLR_TEXT_INFO, "WARN": _CLR_WARNING, "ERROR": _CLR_ERROR}
        tag = ""
        for t in color_map:
            if f"[{t}]" in message:
                tag = t
                break
        color = color_map.get(tag, _CLR_TEXT_INFO)
        self._sc_append_log(message, color)

    @staticmethod
    def _sc_format_bytes(prefix, n):
        if n < 1024:
            return f"{prefix}: {n} B"
        elif n < 1024 * 1024:
            return f"{prefix}: {n / 1024:.1f} KB"
        else:
            return f"{prefix}: {n / (1024 * 1024):.2f} MB"

    # --- ui helpers ---

    @staticmethod
    def _make_sc_btn(svg_path, text, tone="toolbar"):
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        icon_size = 11
        if tone == "log":
            base_color = "#cbd5e1"
            icon_color = "#cbd5e1"
            btn.setStyleSheet(f"""
                QPushButton {{
                    min-height: 0px; max-height: 28px; padding: 5px 11px; border-radius: 7px;
                    background-color: rgba(15, 23, 42, 0.6); color: {base_color}; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 500; border: 1px solid #334155;
                }}
                QPushButton:hover {{ background-color: #1e293b; color: #FFFFFF; border: 1px solid #475569; }}
                QPushButton:focus {{ background-color: #1e293b; color: #FFFFFF; border: 1px solid #818CF8; }}
                QPushButton:pressed {{ background-color: #0f172a; }}
                QPushButton:checked {{ background-color: #1e293b; color: #FFFFFF; border: 1px solid #475569; }}
            """)
        elif tone == "quick":
            base_color = "#cbd5e1"
            icon_color = "#cbd5e1"
            btn.setStyleSheet(f"""
                QPushButton {{
                    min-height: 0px; max-height: 26px; padding: 4px 11px; border-radius: 6px;
                    background-color: #202d3f; color: {base_color}; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 500; border: 1px solid #334155;
                }}
                QPushButton:hover {{ background-color: #314158; color: #FFFFFF; border: 1px solid #475569; }}
                QPushButton:focus {{ background-color: #314158; color: #FFFFFF; border: 1px solid #818CF8; }}
                QPushButton:pressed {{ background-color: #1a2538; }}
                QPushButton:checked {{ background-color: #314158; color: #FFFFFF; border: 1px solid #475569; }}
                QPushButton:disabled {{ background-color: #151c2a; color: #475569; border: 1px solid #1e293b; }}
            """)
        else:
            base_color = "#94a3b8"
            icon_color = "#94a3b8"
            icon_size = 13
            btn.setStyleSheet(f"""
                QPushButton {{
                    min-height: 0px; max-height: 30px; padding: 4px 10px; border-radius: 6px;
                    background-color: transparent; color: {base_color}; font-size: 12px;
                    font-family: {_UI_FONT}; font-weight: 500; border: none;
                }}
                QPushButton:hover {{ border: 1px solid #334155; color: #FFFFFF; }}
                QPushButton:focus {{ border: 1px solid #818CF8; color: #FFFFFF; background-color: #0f172a; }}
                QPushButton:pressed {{ background-color: #050b1e; }}
                QPushButton:checked {{ border: 1px solid #334155; color: #FFFFFF; }}
            """)
        icon = _tinted_svg_icon(svg_path, icon_color, icon_size)
        if not icon.isNull():
            btn.setIcon(icon)
        return btn

    @staticmethod
    def _make_sc_section(title):
        grp = QFrame()
        grp.setObjectName("scSectionCard")
        grp.setStyleSheet("""
            QFrame#scSectionCard {
                background-color: rgba(15, 23, 42, 0.4);
                border: 1px solid rgba(30, 41, 59, 0.8);
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: #94a3b8; font-size: 12px; font-weight: 700; font-family: {_UI_FONT}; background: transparent; border: none; margin-bottom: 4px;")
        layout.addWidget(lbl)

        grp.setProperty("_inner_layout", layout)
        return grp

    @staticmethod
    def _make_sc_label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: #94a3b8; font-size: 12px; font-family: {_UI_FONT}; background: transparent; border: none;")
        return lbl

    @staticmethod
    def _sc_checkbox_style():
        _chk_svg = os.path.join(_SVG_SERIAL_DIR, "checkmark.svg").replace("\\", "/")
        return (
            f"QCheckBox {{ color: #94a3b8; font-size: 12px; font-family: {_UI_FONT}; background: transparent; spacing: 4px; }}"
            f"QCheckBox::indicator {{"
            f"  width: 12px; height: 12px;"
            f"  border: 1px solid #1e293b; border-radius: 2px;"
            f"  background-color: #020618;"
            f"}}"
            f"QCheckBox::indicator:hover {{"
            f"  border-color: #334155;"
            f"}}"
            f"QCheckBox::indicator:checked {{"
            f"  background-color: #6366f1; border-color: #6366f1;"
            f"  image: url({_chk_svg});"
            f"}}"
        )


class _MiniSlideToggle(QWidget):
    toggled = Signal(str)

    def __init__(self, left="ASCII", right="HEX", parent=None):
        super().__init__(parent)
        self._left = left
        self._right = right
        self._value = left
        self._anim_progress = 0.0

        self.setFixedSize(80, 22)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"animProgress")
        self._anim.setDuration(160)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_anim_progress(self):
        return self._anim_progress

    def _set_anim_progress(self, val):
        self._anim_progress = val
        self.update()

    animProgress = Property(float, _get_anim_progress, _set_anim_progress)

    def value(self):
        return self._value

    def set_value(self, val):
        if val not in (self._left, self._right):
            return
        if val == self._value:
            return
        self._value = val
        target = 1.0 if val == self._right else 0.0
        self._anim.stop()
        self._anim.setStartValue(self._anim_progress)
        self._anim.setEndValue(target)
        self._anim.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            new_val = self._right if self._value == self._left else self._left
            self._value = new_val
            target = 1.0 if new_val == self._right else 0.0
            self._anim.stop()
            self._anim.setStartValue(self._anim_progress)
            self._anim.setEndValue(target)
            self._anim.start()
            self.toggled.emit(self._value)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        outer_r = 4

        p.setPen(QPen(QColor("#1e293b"), 1))
        p.setBrush(QColor("#020618"))
        p.drawRoundedRect(QRectF(0, 0, w, h), outer_r, outer_r)

        knob_margin = 2
        knob_h = h - knob_margin * 2
        knob_w = w / 2 - knob_margin
        knob_x = knob_margin + self._anim_progress * (w / 2)
        knob_r = 3

        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#6366f1"))
        p.drawRoundedRect(QRectF(knob_x, knob_margin, knob_w, knob_h),
                          knob_r, knob_r)

        font = p.font()
        font.setPixelSize(10)
        font.setWeight(QFont.Bold)
        p.setFont(font)

        left_rect = QRectF(0, 0, w / 2, h)
        right_rect = QRectF(w / 2, 0, w / 2, h)

        p.setPen(QColor("#FFFFFF") if self._anim_progress < 0.5 else QColor("#94a3b8"))
        p.drawText(left_rect, Qt.AlignCenter, self._left)

        p.setPen(QColor("#FFFFFF") if self._anim_progress >= 0.5 else QColor("#94a3b8"))
        p.drawText(right_rect, Qt.AlignCenter, self._right)

        p.end()


_DLG_CHK_SVG = os.path.join(_SVG_SERIAL_DIR, "checkmark.svg").replace("\\", "/")
_DLG_STYLE = f"""
    QDialog {{
        background-color: #050b1e;
        color: #cbd5e1;
    }}
    QLabel {{ color: #94a3b8; font-size: 12px; font-family: {_UI_FONT}; background: transparent; }}
    QLabel#dlgSectionTitle {{
        color: #94a3b8; font-size: 13px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;
        padding-bottom: 2px;
    }}
    QFrame#dlgSep {{ background-color: #1e293b; }}
    QCheckBox {{ color: #94a3b8; font-size: 12px; font-family: {_UI_FONT}; background: transparent; spacing: 4px; }}
    QCheckBox::indicator {{
        width: 13px; height: 13px;
        border: 1px solid #1e293b; border-radius: 2px;
        background-color: #020618;
    }}
    QCheckBox::indicator:hover {{ border-color: #334155; }}
    QCheckBox::indicator:checked {{
        background-color: #6366f1; border-color: #6366f1;
        image: url({_DLG_CHK_SVG});
    }}
    QSpinBox {{
        background-color: #020618; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
        color: #cbd5e1; font-size: 12px; font-family: {_UI_FONT}; padding: 2px 6px;
    }}
    QSpinBox::up-button, QSpinBox::down-button {{ width: 12px; }}
    QPushButton#dlgOkBtn {{
        background-color: #10b981; border: none; border-radius: 4px;
        color: #FFFFFF; font-weight: 700; font-size: 13px; font-family: {_UI_FONT}; padding: 5px 18px;
    }}
    QPushButton#dlgOkBtn:hover {{ background-color: #059669; }}
    QPushButton#dlgCancelBtn {{
        background-color: transparent; border: 1px solid #1e293b; border-radius: 4px;
        color: #94a3b8; font-size: 13px; font-family: {_UI_FONT}; padding: 5px 18px;
    }}
    QPushButton#dlgCancelBtn:hover {{ border-color: #334155; color: #FFFFFF; }}
    QTabWidget::pane {{
        background-color: #050b1e;
        border: 1px solid #1e293b;
        border-radius: 4px;
        padding: 4px;
    }}
    QTabBar::tab {{
        background-color: #050b1e;
        color: #94a3b8;
        padding: 5px 14px;
        border: none;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        font-size: 13px;
        font-family: {_UI_FONT};
        font-weight: 500;
        margin-right: 2px;
    }}
    QTabBar::tab:hover {{
        background-color: #050b1e;
        color: #cbd5e1;
    }}
    QTabBar::tab:selected {{
        background-color: #050b1e;
        color: #FFFFFF;
        border-bottom: 2px solid #6366f1;
    }}
"""


class _AddLogPanelDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add LOG Panel")
        self.setFixedWidth(400)
        self.setStyleSheet(_DLG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("New Serial LOG")
        title.setObjectName("dlgSectionTitle")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Panel Name"), 0, 0)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g. LOG-2")
        self._title_edit.setText("Serial Log 2")
        self._title_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: #020618; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
                color: #cbd5e1; font-size: 13px; font-family: {_UI_FONT}; padding: 5px 8px; min-height: 24px;
            }}
            QLineEdit:focus {{ border: 1px solid #334155; }}
        """)
        grid.addWidget(self._title_edit, 0, 1)

        grid.addWidget(QLabel("Port"), 1, 0)
        self._port_combo = DarkComboBox()
        self._port_combo.setFixedHeight(26)
        self._port_combo.setEditable(True)
        try:
            ports = serial.tools.list_ports.comports()
            for p in ports:
                self._port_combo.addItem(f"{p.device} - {p.description}")
        except Exception:
            pass
        if self._port_combo.count() == 0:
            if DEBUG_MOCK:
                self._port_combo.addItem("[MOCK] COM99 - Mock Serial Device")
            else:
                self._port_combo.addItem("No serial ports found")
        grid.addWidget(self._port_combo, 1, 1)

        grid.addWidget(QLabel("Baudrate"), 2, 0)
        self._baud_combo = DarkComboBox()
        self._baud_combo.setFixedHeight(26)
        self._baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000"]:
            self._baud_combo.addItem(br)
        self._baud_combo.setCurrentIndex(0)
        grid.addWidget(self._baud_combo, 2, 1)

        grid.addWidget(QLabel("Data bits"), 3, 0)
        self._databit_combo = DarkComboBox()
        self._databit_combo.setFixedHeight(26)
        for d in ["8", "7", "6", "5"]:
            self._databit_combo.addItem(d)
        grid.addWidget(self._databit_combo, 3, 1)

        grid.addWidget(QLabel("Stop bits"), 4, 0)
        self._stopbit_combo = DarkComboBox()
        self._stopbit_combo.setFixedHeight(26)
        for s in ["1", "1.5", "2"]:
            self._stopbit_combo.addItem(s)
        grid.addWidget(self._stopbit_combo, 4, 1)

        grid.addWidget(QLabel("Parity"), 5, 0)
        self._parity_combo = DarkComboBox()
        self._parity_combo.setFixedHeight(26)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._parity_combo.addItem(p)
        grid.addWidget(self._parity_combo, 5, 1)

        grid.addWidget(QLabel("Flow Control"), 6, 0)
        self._flow_combo = DarkComboBox()
        self._flow_combo.setFixedHeight(26)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._flow_combo.addItem(fc)
        grid.addWidget(self._flow_combo, 6, 1)

        root.addLayout(grid)

        self._auto_connect_cb = QCheckBox("Auto connect after creation")
        self._auto_connect_cb.setChecked(True)
        root.addWidget(self._auto_connect_cb)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dlgCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("dlgOkBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    def get_config(self):
        port_text = self._port_combo.currentText()
        port = port_text.split()[0] if port_text and not port_text.startswith("No ") else ""
        try:
            baudrate = int(self._baud_combo.currentText().strip())
        except ValueError:
            baudrate = 115200
        return {
            "title": self._title_edit.text().strip() or "Serial Log",
            "port": port,
            "baudrate": baudrate,
            "databit": int(self._databit_combo.currentText()),
            "stopbit": self._stopbit_combo.currentText(),
            "parity": self._parity_combo.currentText(),
            "flow": self._flow_combo.currentText(),
            "auto_connect": self._auto_connect_cb.isChecked(),
        }


class _QuickCmdButton(QPushButton):
    """支持右键菜单 + 拖拽排序的快捷指令按钮。

    - 左键短按 → 触发 ``clicked``（发送指令，逻辑在宿主信号槽里）；
    - 左键拖动超过阈值 → 启动 ``QDrag``，mime 携带源索引；
    - 右键 → 通过 ``Qt.CustomContextMenu`` 上抛给宿主弹出 Edit / Delete 菜单。

    数据流：源索引由宿主在创建按钮时通过 ``set_command_index`` 注入。
    """

    _MIME_TYPE = "application/x-kklab-quickcmd"

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(False)  # 容器统一接收 drop，按钮自身不参与
        self._press_pos = None
        self._cmd_index = -1
        self._dragging = False

    def set_command_index(self, idx: int):
        self._cmd_index = idx

    def command_index(self) -> int:
        return self._cmd_index

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.LeftButton
            and self._press_pos is not None
            and not self._dragging
            and self._cmd_index >= 0
        ):
            if (
                event.position().toPoint() - self._press_pos
            ).manhattanLength() >= QApplication.startDragDistance():
                self._dragging = True
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        # 拖拽中按下释放不触发 click（Qt 会自动把 release 派发给 drop 目标）
        was_dragging = self._dragging
        self._press_pos = None
        self._dragging = False
        if was_dragging:
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _start_drag(self):
        from PySide6.QtGui import QDrag  # 局部引入
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self._MIME_TYPE, str(self._cmd_index).encode())
        drag.setMimeData(mime)
        pixmap = self.grab()
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec(Qt.MoveAction)


class _ProjectTabBar(QTabBar):
    """支持右键菜单 + 项目 Tab 拖拽排序的 QTabBar 子类。

    - 拖拽：按下左键 + 移动超过阈值则启动；放下时计算源 / 目标 index 并通过
      ``project_reorder_requested(source, target)`` 发射给宿主，由宿主修改
      数据模型后重建 Tab。
    - 拖拽时排除末尾的 "+" 加号 tab（最后一项）。
    - 右键菜单：通过 ``Qt.CustomContextMenu`` 上抛给宿主统一处理。
    """

    project_reorder_requested = Signal(int, int)
    _MIME_TYPE = "application/x-kklab-project-tab"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMovable(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self._press_pos = None
        self._press_index = -1

    def _is_real_tab(self, index: int) -> bool:
        # 约定：最后一个 tab 为 "+" 加号，不参与拖拽
        return 0 <= index < self.count() - 1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self.tabAt(event.position().toPoint())
            if self._is_real_tab(idx):
                self._press_pos = event.position().toPoint()
                self._press_index = idx
            else:
                self._press_pos = None
                self._press_index = -1
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.LeftButton
            and self._press_pos is not None
            and self._press_index >= 0
        ):
            if (
                event.position().toPoint() - self._press_pos
            ).manhattanLength() >= QApplication.startDragDistance():
                self._start_drag(self._press_index)
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        self._press_index = -1
        super().mouseReleaseEvent(event)

    def _start_drag(self, source_index: int):
        from PySide6.QtGui import QDrag  # 局部引入，避免顶部模块持有未用符号
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self._MIME_TYPE, str(source_index).encode())
        drag.setMimeData(mime)
        rect = self.tabRect(source_index)
        if not rect.isEmpty():
            pixmap = self.grab(rect)
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(rect.width() // 2, rect.height() // 2))
        drag.exec(Qt.MoveAction)
        self._press_pos = None
        self._press_index = -1

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self._MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(self._MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self._MIME_TYPE):
            return
        try:
            source_index = int(
                bytes(event.mimeData().data(self._MIME_TYPE)).decode()
            )
        except (ValueError, UnicodeDecodeError):
            return
        target_index = self.tabAt(event.position().toPoint())
        # 拖到 "+" tab 或外部 → 视为挪到末尾真实项目
        last_real = self.count() - 2
        if not self._is_real_tab(target_index):
            target_index = last_real if last_real >= 0 else 0
        if source_index == target_index:
            return
        event.acceptProposedAction()
        self.project_reorder_requested.emit(source_index, target_index)


class _QuickCmdDialog(QDialog):

    def __init__(self, parent=None, name="", content="", send_type="text",
                 line_ending="\r\n", encoding="ascii"):
        super().__init__(parent)
        self.setWindowTitle("Quick Command")
        self.setFixedWidth(380)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #050b1e;
                color: #cbd5e1;
            }}
            QLabel {{
                color: #94a3b8; font-size: 12px; font-family: {_UI_FONT}; background: transparent;
            }}
            QLabel#qcTitle {{
                color: #94a3b8; font-size: 13px; font-weight: 700; font-family: {_UI_FONT}; background: transparent;
            }}
            QLineEdit {{
                background-color: #020618; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
                color: #cbd5e1; font-size: 13px; font-family: {_UI_FONT}; padding: 5px 8px; min-height: 24px;
            }}
            QLineEdit:focus {{ border: 1px solid #334155; }}
            QComboBox {{
                background-color: #020618; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
                color: #cbd5e1; font-size: 13px; font-family: {_UI_FONT}; padding: 4px 8px; min-height: 24px;
            }}
            QComboBox:hover {{ border-color: #334155; }}
            QComboBox QAbstractItemView {{
                background-color: #020618; color: #cbd5e1;
                border: 1px solid #1e293b; selection-background-color: #1e293b;
                outline: 0;
            }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        is_edit = bool(name or content)
        title = QLabel("Edit Quick Command" if is_edit else "New Quick Command")
        title.setObjectName("qcTitle")
        root.addWidget(title)

        root.addWidget(QLabel("指令名称"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如:查询版本")
        self._name_edit.setText(name)
        root.addWidget(self._name_edit)

        root.addWidget(QLabel("指令内容"))
        self._cmd_edit = QLineEdit()
        self._cmd_edit.setPlaceholderText("如:AT+GMR")
        self._cmd_edit.setText(content)
        root.addWidget(self._cmd_edit)

        root.addWidget(QLabel("发送方式"))
        self._send_type_combo = QComboBox()
        # 显示文案大写（TEXT / HEX），userData 保持小写以兼容旧数据
        self._send_type_combo.addItem("TEXT", "text")
        self._send_type_combo.addItem("HEX", "hex")
        idx = self._send_type_combo.findData(send_type)
        self._send_type_combo.setCurrentIndex(idx if idx >= 0 else 0)
        root.addWidget(self._send_type_combo)

        root.addWidget(QLabel("结尾符"))
        self._line_ending_combo = QComboBox()
        self._line_ending_combo.addItem("无", "")
        self._line_ending_combo.addItem("\\r", "\r")
        self._line_ending_combo.addItem("\\n", "\n")
        self._line_ending_combo.addItem("\\r\\n", "\r\n")
        idx = self._line_ending_combo.findData(line_ending)
        self._line_ending_combo.setCurrentIndex(idx if idx >= 0 else 3)
        root.addWidget(self._line_ending_combo)

        root.addWidget(QLabel("编码"))
        self._encoding_combo = QComboBox()
        # 默认 ascii，放在第一位以便 setCurrentIndex(0) 兜底命中
        # 显示文案大写（ASCII / UTF-8 / GBK），userData 保持小写以兼容旧数据
        for enc_label, enc_value in (("ASCII", "ascii"), ("UTF-8", "utf-8"), ("GBK", "gbk")):
            self._encoding_combo.addItem(enc_label, enc_value)
        idx = self._encoding_combo.findData(encoding)
        self._encoding_combo.setCurrentIndex(idx if idx >= 0 else 0)
        root.addWidget(self._encoding_combo)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: 1px solid #1e293b; border-radius: 4px;
                color: #94a3b8; font-size: 13px; font-family: {_UI_FONT}; padding: 5px 18px;
            }}
            QPushButton:hover {{ border-color: #334155; color: #FFFFFF; }}
        """)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #10b981; border: none; border-radius: 4px;
                color: #FFFFFF; font-weight: 700; font-size: 13px; font-family: {_UI_FONT}; padding: 5px 18px;
            }}
            QPushButton:hover {{ background-color: #059669; }}
        """)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    def get_command(self) -> dict:
        return {
            "name": self._name_edit.text().strip(),
            "content": self._cmd_edit.text(),
            "send_type": self._send_type_combo.currentData() or "text",
            "line_ending": self._line_ending_combo.currentData() or "",
            "encoding": self._encoding_combo.currentData() or "ascii",
        }

    # 兼容老调用 (已无人使用)
    def get_name(self):
        return self._name_edit.text().strip()

    def get_cmd(self):
        return self._cmd_edit.text().strip()


class _SerialSettingsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Serial Settings")
        self.setMinimumSize(480, 420)
        self.setStyleSheet(_DLG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self._tabs = QTabWidget()
        root.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_tab_serial(), "Serial")
        self._tabs.addTab(self._build_tab_rx(), "RX")
        self._tabs.addTab(self._build_tab_tx(), "TX")
        self._tabs.addTab(self._build_tab_log(), "Log")
        self._tabs.addTab(self._build_tab_display(), "Display")
        self._tabs.addTab(self._build_tab_auto_detect(), "Auto-Detect")

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("dlgCancelBtn")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("dlgOkBtn")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    # ---- tab: Serial ----

    def _build_tab_serial(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Connection"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Port"), 0, 0)
        self.port_combo = DarkComboBox()
        self.port_combo.setFixedHeight(26)
        grid.addWidget(self.port_combo, 0, 1)

        grid.addWidget(QLabel("Baudrate"), 1, 0)
        self.baud_combo = DarkComboBox()
        self.baud_combo.setFixedHeight(26)
        self.baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000", "Custom"]:
            self.baud_combo.addItem(br)
        grid.addWidget(self.baud_combo, 1, 1)

        layout.addLayout(grid)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Advanced"))

        adv_grid = QGridLayout()
        adv_grid.setHorizontalSpacing(12)
        adv_grid.setVerticalSpacing(8)

        adv_grid.addWidget(QLabel("Data bits"), 0, 0)
        self.databit_combo = DarkComboBox()
        self.databit_combo.setFixedHeight(26)
        for d in ["8", "7", "6", "5"]:
            self.databit_combo.addItem(d)
        adv_grid.addWidget(self.databit_combo, 0, 1)

        adv_grid.addWidget(QLabel("Stop bits"), 0, 2)
        self.stopbit_combo = DarkComboBox()
        self.stopbit_combo.setFixedHeight(26)
        for s in ["1", "1.5", "2"]:
            self.stopbit_combo.addItem(s)
        adv_grid.addWidget(self.stopbit_combo, 0, 3)

        adv_grid.addWidget(QLabel("Parity"), 1, 0)
        self.parity_combo = DarkComboBox()
        self.parity_combo.setFixedHeight(26)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self.parity_combo.addItem(p)
        adv_grid.addWidget(self.parity_combo, 1, 1)

        adv_grid.addWidget(QLabel("Flow Control"), 1, 2)
        self.flow_combo = DarkComboBox()
        self.flow_combo.setFixedHeight(26)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self.flow_combo.addItem(fc)
        adv_grid.addWidget(self.flow_combo, 1, 3)

        layout.addLayout(adv_grid)
        layout.addStretch()
        return page

    # ---- tab: RX ----

    def _build_tab_rx(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Data Format"))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Encoding"))
        self.rx_hex_toggle = _MiniSlideToggle("ASCII", "HEX")
        row.addWidget(self.rx_hex_toggle)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Timestamp"))

        self.show_time_cb = QCheckBox("Show timestamp (ms precision)")
        layout.addWidget(self.show_time_cb)

        self.rx_use_ntp_cb = QCheckBox("Use network time (NTP calibrated)")
        layout.addWidget(self.rx_use_ntp_cb)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Buffer"))

        buf_row = QHBoxLayout()
        buf_row.setSpacing(8)
        buf_row.addWidget(QLabel("Max lines"))
        self.rx_max_lines_spin = QSpinBox()
        self.rx_max_lines_spin.setRange(500, 100000)
        self.rx_max_lines_spin.setValue(10000)
        self.rx_max_lines_spin.setSingleStep(1000)
        self.rx_max_lines_spin.setFixedHeight(26)
        buf_row.addWidget(self.rx_max_lines_spin)
        buf_row.addStretch()
        layout.addLayout(buf_row)

        layout.addStretch()
        return page

    # ---- tab: TX ----

    def _build_tab_tx(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Data Format"))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Encoding"))
        self.tx_hex_toggle = _MiniSlideToggle("ASCII", "HEX")
        row.addWidget(self.tx_hex_toggle)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Line Ending & Auto Resend"))

        ending_row = QHBoxLayout()
        ending_row.setSpacing(8)
        ending_row.addWidget(QLabel("Line ending"))
        self.ending_combo = DarkComboBox()
        self.ending_combo.setFixedHeight(26)
        for label, val in [("\\r\\n", "\r\n"), ("\\n", "\n"), ("\\r", "\r"), ("\\n\\r", "\n\r"), ("None", "")]:
            self.ending_combo.addItem(label, val)
        ending_row.addWidget(self.ending_combo)
        ending_row.addStretch()
        layout.addLayout(ending_row)

        self.auto_resend_cb = QCheckBox("Enable auto resend")
        layout.addWidget(self.auto_resend_cb)

        resend_row = QHBoxLayout()
        resend_row.setSpacing(8)
        resend_row.addWidget(QLabel("Resend interval (ms)"))
        self.resend_spin = QSpinBox()
        self.resend_spin.setRange(100, 60000)
        self.resend_spin.setValue(1000)
        self.resend_spin.setSingleStep(100)
        self.resend_spin.setFixedHeight(26)
        resend_row.addWidget(self.resend_spin)
        resend_row.addStretch()
        layout.addLayout(resend_row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Other"))

        self.show_send_cb = QCheckBox("Show sent data in log")
        layout.addWidget(self.show_send_cb)

        self.line_by_line_cb = QCheckBox("Line by Line (split by \\n for multi-line send)")
        layout.addWidget(self.line_by_line_cb)

        layout.addStretch()
        return page

    # ---- tab: Log ----

    def _build_tab_log(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Log File"))

        self.log_auto_save_cb = QCheckBox("Auto save log to file")
        layout.addWidget(self.log_auto_save_cb)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        path_row.addWidget(QLabel("Save path"))
        self.log_save_path_edit = QLineEdit()
        self.log_save_path_edit.setPlaceholderText("Select log save directory...")
        self.log_save_path_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: #020618; border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 4px;
                color: #cbd5e1; font-size: 12px; font-family: {_UI_FONT}; padding: 3px 6px; min-height: 22px;
            }}
            QLineEdit:focus {{ border: 1px solid #334155; }}
        """)
        path_row.addWidget(self.log_save_path_edit, 1)
        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setObjectName("dlgCancelBtn")
        browse_btn.setAutoDefault(False)
        browse_btn.setDefault(False)
        browse_btn.clicked.connect(self._browse_log_path)
        path_row.addWidget(browse_btn)
        layout.addLayout(path_row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Log Level Colors"))

        color_info = QLabel(
            "RX → Emerald (#10b981)    TX → Blue (#60a5fa)\n"
            "INFO → Slate (#94a3b8)    WARN → Amber (#f59e0b)    ERROR → Rose (#f43f5e)"
        )
        color_info.setStyleSheet(f"color: #94a3b8; font-size: 11px; font-family: {_UI_FONT}; background: transparent;")
        color_info.setWordWrap(True)
        layout.addWidget(color_info)

        layout.addStretch()
        return page

    # ---- tab: Display ----

    def _build_tab_display(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Font"))

        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        font_row.addWidget(QLabel("Font family"))
        self.display_font_combo = DarkComboBox()
        self.display_font_combo.setFixedHeight(26)
        for f in ["Consolas", "Courier New", "Fira Code", "JetBrains Mono", "Cascadia Code", "Lucida Console"]:
            self.display_font_combo.addItem(f)
        font_row.addWidget(self.display_font_combo)
        font_row.addStretch()
        layout.addLayout(font_row)

        size_row = QHBoxLayout()
        size_row.setSpacing(8)
        size_row.addWidget(QLabel("Font size"))
        self.display_font_size_spin = QSpinBox()
        self.display_font_size_spin.setRange(8, 24)
        self.display_font_size_spin.setValue(11)
        self.display_font_size_spin.setFixedHeight(26)
        size_row.addWidget(self.display_font_size_spin)
        size_row.addStretch()
        layout.addLayout(size_row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Behavior"))

        self.display_auto_scroll_cb = QCheckBox("Enable auto-scroll by default")
        self.display_auto_scroll_cb.setChecked(True)
        layout.addWidget(self.display_auto_scroll_cb)

        self.display_word_wrap_cb = QCheckBox("Word Wrap")
        self.display_word_wrap_cb.setChecked(True)
        layout.addWidget(self.display_word_wrap_cb)

        self.display_show_line_num_cb = QCheckBox("Show line numbers")
        layout.addWidget(self.display_show_line_num_cb)

        layout.addStretch()
        return page

    # ---- tab: Auto-Detect ----

    def _build_tab_auto_detect(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        layout.addWidget(self._section_title("Auto Baudrate Detection"))

        self.auto_detect_enable_cb = QCheckBox("Enable auto baudrate detection")
        layout.addWidget(self.auto_detect_enable_cb)

        self.auto_detect_runtime_cb = QCheckBox("Allow runtime auto re-detection")
        layout.addWidget(self.auto_detect_runtime_cb)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Candidate Baudrates"))

        self.auto_detect_candidates_edit = QLineEdit()
        self.auto_detect_candidates_edit.setPlaceholderText("e.g. 921600, 1152000, 2000000, 3000000")
        self.auto_detect_candidates_edit.setText(
            ", ".join(str(b) for b in AUTO_BAUD_CONFIG["candidate_baudrates"])
        )
        layout.addWidget(self.auto_detect_candidates_edit)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Thresholds"))

        thresh_grid = QGridLayout()
        thresh_grid.setHorizontalSpacing(12)
        thresh_grid.setVerticalSpacing(8)

        thresh_grid.addWidget(QLabel("Lock threshold"), 0, 0)
        self.auto_detect_lock_spin = QSpinBox()
        self.auto_detect_lock_spin.setRange(50, 100)
        self.auto_detect_lock_spin.setValue(AUTO_BAUD_CONFIG["lock_threshold"])
        self.auto_detect_lock_spin.setFixedHeight(26)
        thresh_grid.addWidget(self.auto_detect_lock_spin, 0, 1)

        thresh_grid.addWidget(QLabel("Bad threshold"), 0, 2)
        self.auto_detect_bad_spin = QSpinBox()
        self.auto_detect_bad_spin.setRange(10, 80)
        self.auto_detect_bad_spin.setValue(AUTO_BAUD_CONFIG["bad_threshold"])
        self.auto_detect_bad_spin.setFixedHeight(26)
        thresh_grid.addWidget(self.auto_detect_bad_spin, 0, 3)

        thresh_grid.addWidget(QLabel("Bad windows to suspect"), 1, 0)
        self.auto_detect_bad_windows_spin = QSpinBox()
        self.auto_detect_bad_windows_spin.setRange(1, 10)
        self.auto_detect_bad_windows_spin.setValue(AUTO_BAUD_CONFIG["bad_windows_to_suspect"])
        self.auto_detect_bad_windows_spin.setFixedHeight(26)
        thresh_grid.addWidget(self.auto_detect_bad_windows_spin, 1, 1)

        thresh_grid.addWidget(QLabel("Suspect windows to scan"), 1, 2)
        self.auto_detect_suspect_windows_spin = QSpinBox()
        self.auto_detect_suspect_windows_spin.setRange(1, 10)
        self.auto_detect_suspect_windows_spin.setValue(AUTO_BAUD_CONFIG["suspect_windows_to_scan"])
        self.auto_detect_suspect_windows_spin.setFixedHeight(26)
        thresh_grid.addWidget(self.auto_detect_suspect_windows_spin, 1, 3)

        layout.addLayout(thresh_grid)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Timing"))

        time_grid = QGridLayout()
        time_grid.setHorizontalSpacing(12)
        time_grid.setVerticalSpacing(8)

        time_grid.addWidget(QLabel("Monitor window (ms)"), 0, 0)
        self.auto_detect_window_ms_spin = QSpinBox()
        self.auto_detect_window_ms_spin.setRange(100, 2000)
        self.auto_detect_window_ms_spin.setValue(AUTO_BAUD_CONFIG["monitor_window_max_time_ms"])
        self.auto_detect_window_ms_spin.setFixedHeight(26)
        time_grid.addWidget(self.auto_detect_window_ms_spin, 0, 1)

        time_grid.addWidget(QLabel("Switch cooldown (ms)"), 0, 2)
        self.auto_detect_cooldown_spin = QSpinBox()
        self.auto_detect_cooldown_spin.setRange(1000, 30000)
        self.auto_detect_cooldown_spin.setSingleStep(500)
        self.auto_detect_cooldown_spin.setValue(AUTO_BAUD_CONFIG["switch_cooldown_ms"])
        self.auto_detect_cooldown_spin.setFixedHeight(26)
        time_grid.addWidget(self.auto_detect_cooldown_spin, 0, 3)

        time_grid.addWidget(QLabel("Score margin"), 1, 0)
        self.auto_detect_margin_spin = QSpinBox()
        self.auto_detect_margin_spin.setRange(5, 60)
        self.auto_detect_margin_spin.setValue(AUTO_BAUD_CONFIG["switch_score_margin"])
        self.auto_detect_margin_spin.setFixedHeight(26)
        time_grid.addWidget(self.auto_detect_margin_spin, 1, 1)

        time_grid.addWidget(QLabel("Confirm rounds"), 1, 2)
        self.auto_detect_confirm_spin = QSpinBox()
        self.auto_detect_confirm_spin.setRange(1, 5)
        self.auto_detect_confirm_spin.setValue(AUTO_BAUD_CONFIG["confirm_scan_rounds"])
        self.auto_detect_confirm_spin.setFixedHeight(26)
        time_grid.addWidget(self.auto_detect_confirm_spin, 1, 3)

        layout.addLayout(time_grid)

        layout.addStretch()
        return page

    # ---- helpers ----

    def _browse_log_path(self):
        path = QFileDialog.getExistingDirectory(self, "Select Log Save Directory")
        if path:
            self.log_save_path_edit.setText(path)

    @staticmethod
    def _section_title(text):
        lbl = QLabel(text)
        lbl.setObjectName("dlgSectionTitle")
        return lbl

    @staticmethod
    def _separator():
        sep = QFrame()
        sep.setObjectName("dlgSep")
        sep.setFrameShape(QFrame.HLine)
        sep.setFixedHeight(1)
        return sep


class _SerialReadWorker(QObject):
    data_received = Signal(bytes)
    error = Signal(str)

    def __init__(self, serial_conn):
        super().__init__()
        self._serial_conn = serial_conn
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                if self._serial_conn is None or not self._serial_conn.is_open:
                    break
                if self._serial_conn.in_waiting > 0:
                    data = self._serial_conn.read(self._serial_conn.in_waiting)
                    if data:
                        self.data_received.emit(data)
                else:
                    QThread.msleep(50)
            except Exception as e:
                if self._running:
                    self.error.emit(str(e))
                break


if __name__ == "__main__":
    #python -m ui.modules.serialCom_module_frame
    import sys
    from PySide6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QFrame, QSizePolicy
    )

    DARK_CARD_STYLE = f"""
        QWidget {{
            background-color: #0a0a0a;
            color: #ccc;
        }}
        QLabel {{
            background-color: transparent;
            color: #ccc;
            border: none;
        }}
        QLabel#statusOk {{
            color: #10b981;
            font-weight: 500;
            background-color: transparent;
        }}
        QLabel#statusWarn {{
            color: #f59e0b;
            font-weight: 500;
            background-color: transparent;
        }}
        QLabel#statusErr {{
            color: #f43f5e;
            font-weight: 500;
            background-color: transparent;
        }}
        QFrame#cardFrame {{
            background-color: #111;
            border: 1px solid #222;
            border-radius: 4px;
        }}
        QComboBox {{
            background-color: #1a1a1a;
            color: #ccc;
            border: 1px solid #2a2a2a;
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 20px;
            background: transparent;
        }}
        QComboBox QAbstractItemView {{
            background-color: #1a1a1a;
            color: #ccc;
            border: 1px solid #2a2a2a;
            selection-background-color: #333;
        }}
    """

    class _CardFrame(QFrame):
        def __init__(self, title="", parent=None):
            super().__init__(parent)
            self.setObjectName("cardFrame")
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(12, 10, 12, 12)
            self.main_layout.setSpacing(8)
            if title:
                self.title_row = QHBoxLayout()
                self.title_row.setSpacing(8)
                self.title_label = QLabel(title)
                self.title_label.setObjectName("cardTitle")
                self.title_row.addWidget(self.title_label)
                self.title_row.addStretch()
                self.main_layout.addLayout(self.title_row)
            else:
                self.title_label = None
                self.title_row = None

    demo_logger = get_logger(f"{__name__}.demo")

    class _DemoSerialFullWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_FULL, prefix="FullDemo")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Serial (Full Mode)")
            self.build_serial_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_serial_signals()

        def append_log(self, msg):
            demo_logger.info(msg)

    class _DemoSerialSearchWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_SEARCH_SELECT, prefix="SearchDemo")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Serial (Search & Select Mode)")
            self.build_serial_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_serial_signals()

        def append_log(self, msg):
            demo_logger.info(msg)

    class _DemoSerialInlineWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_INLINE, prefix="InlineDemo")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)

            card = _CardFrame("Serial (Inline Mode)")
            self.build_serial_connection_widgets(card.main_layout)
            root.addWidget(card)
            root.addStretch()

            self.bind_serial_signals()

        def append_log(self, msg):
            demo_logger.info(msg)

    class _DemoCompleteSerialWidget(SerialComMixin, QWidget):
        serial_connection_changed = Signal(bool)
        serial_data_received = Signal(bytes)

        def __init__(self, parent=None):
            super().__init__(parent)
            self.init_serial_connection(mode=MODE_FULL, prefix="Complete")
            self.setStyleSheet(DARK_CARD_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(0, 0, 0, 0)
            self.complete_serialComWidget(root)

            self._sc_on_refresh()
            self._sc_append_system("[INFO] KK Serials initialized")

        def append_log(self, msg):
            self._sc_append_system(msg)

        def closeEvent(self, event):
            try:
                self._sc_save_persisted_state()
            except Exception:
                pass
            super().closeEvent(event)

    from PySide6.QtCore import QtMsgType, qInstallMessageHandler

    def _custom_message_handler(msg_type, context, message):
        if msg_type == QtMsgType.QtWarningMsg and "QPainter::end" in message:
            return
        demo_logger.warning(message)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    qInstallMessageHandler(_custom_message_handler)

    _ICON_PATH = os.path.join(
        get_resource_base(), "resources", "icons", "serialcom_module.ico"
    )
    if os.path.isfile(_ICON_PATH):
        app.setWindowIcon(QIcon(_ICON_PATH))

    w4 = _DemoCompleteSerialWidget()
    w4.setWindowTitle("KK Serial Console")
    if os.path.isfile(_ICON_PATH):
        w4.setWindowIcon(QIcon(_ICON_PATH))
    w4.resize(1125, 750)
    w4.show()
    w4.move(50, 100)

    sys.exit(app.exec())
