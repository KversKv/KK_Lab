#
# python -m ui.modules.serialCom_module_frame
#

import os as _os
import sys as _sys
_PROJECT_ROOT = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))))
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)
from ui.resource_path import get_resource_base as _get_resource_base
from ui.resource_path import get_resource_base
_PROJECT_ROOT = _get_resource_base()
if _PROJECT_ROOT not in _sys.path:
    _sys.path.insert(0, _PROJECT_ROOT)

import json
import importlib as _importlib
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
    QInputDialog, QMessageBox, QTabBar, QGraphicsDropShadowEffect,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QPlainTextEdit,
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

from debug_config import DEBUG_MOCK
from log_config import get_logger
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon


def _select_serialcom_style_module():
    override = _os.environ.get("KK_SERIALCOM_STYLE", "").strip().lower()
    if override in ("apple", "light", "standalone"):
        return "ui.modules.serialCom_module.serialCom_apple_gpt5p5_style"
    if override in ("dark", "main"):
        return "ui.modules.serialCom_module.serialCom_dark_style"

    exe_name = _os.path.splitext(_os.path.basename(getattr(_sys, "executable", "")))[0].lower()
    if __name__ == "__main__" or (getattr(_sys, "frozen", False) and exe_name == "serialcom_module"):
        return "ui.modules.serialCom_module.serialCom_apple_gpt5p5_style"
    return "ui.modules.serialCom_module.serialCom_dark_style"


_SERIALCOM_STYLE_EXPORTS = (
    "DARK_CARD_STYLE", "_CLR_BG_CARD", "_CLR_BG_LOG", "_CLR_BG_MAIN", "_CLR_BG_PANEL",
    "_CLR_BORDER", "_CLR_BORDER_HOVER", "_CLR_CONNECT_BG", "_CLR_CONNECT_FG",
    "_CLR_CONNECT_TEXT", "_CLR_CURSOR", "_CLR_DISCONNECT_TEXT", "_CLR_ERROR",
    "_CLR_FILTER_BG", "_CLR_FILTER_BORDER", "_CLR_FILTER_TEXT", "_CLR_INPUT_BG",
    "_CLR_INPUT_TEXT", "_CLR_ROSE_ICON", "_CLR_RX", "_CLR_SCROLLBAR",
    "_CLR_SCROLLBAR_HV", "_CLR_SELECTION_BG", "_CLR_SELECTION_TEXT", "_CLR_SEND_BG",
    "_CLR_SEND_HOVER", "_CLR_SEND_PRESS", "_CLR_TEXT_ACCENT", "_CLR_TEXT_BODY",
    "_CLR_TEXT_BTN", "_CLR_TEXT_BTN_LOG", "_CLR_TEXT_INFO", "_CLR_TEXT_LABEL",
    "_CLR_TEXT_LINENO", "_CLR_TEXT_MUTED", "_CLR_TEXT_SUBTITLE", "_CLR_TEXT_TIME",
    "_CLR_TEXT_TITLE", "_CLR_TOGGLE_ON", "_CLR_TX", "_CLR_WARN_ICON", "_CLR_WARNING",
    "_DLG_STYLE", "_SERIAL_BTN_HEIGHT", "_SERIAL_BTN_ICON_SIZE", "_SERIAL_BTN_RADIUS",
    "_TERM_FONT", "_UI_FONT", "_serial_connect_style", "_serial_disconnect_style",
    "_serial_search_style", "body_splitter_style", "center_vsplitter_style",
    "center_widget_style",
    "checkbox_style", "compact_spinbox_style", "dialog_cancel_button_style",
    "dialog_line_edit_style", "dialog_ok_button_style", "extra_log_error_color",
    "field_label_style", "filter_input_style", "filter_match_label_style",
    "history_combo_style", "inline_serial_label_style",
    "inline_serial_search_button_extra_style", "log_color_info_style",
    "log_color_info_text", "log_document_style", "log_edit_style", "log_frame_style",
    "log_panel_button_style", "log_title_style", "log_toolbar_button_style",
    "main_connect_button_style", "project_tabs_style", "quick_add_button_style",
    "quick_button_container_style", "quick_button_scroll_style", "quick_cmd_dialog_style",
    "quick_command_button_style", "quick_combo_style", "quick_commands_panel_style",
    "quick_preview_popup_shadow", "quick_preview_popup_style", "quick_toolbar_button_style",
    "bottom_tabs_style",
    "section_card_style", "section_title_style", "send_button_style", "separator_style",
    "sidebar_wrapper_style", "small_label_style", "status_bar_style", "status_label_style",
    "thin_scrollbar_style", "toolbar_connect_button_style", "toolbar_style", "toggle_colors",
    "transparent_background_style", "transparent_scroll_area_style",
    "transparent_toolbar_button_style", "unit_label_style", "SERIAL_SCROLLBAR_STYLE",
    "SerialDarkComboBox",
)

_SERIALCOM_STYLE_MODULE = _select_serialcom_style_module()
_serialcom_style = _importlib.import_module(_SERIALCOM_STYLE_MODULE)
globals().update({
    _name: getattr(_serialcom_style, _name)
    for _name in _SERIALCOM_STYLE_EXPORTS
})
del _serialcom_style
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


class _MixinSerialSettingsDialog(QDialog):
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
        super().__init__(parent)
        self.setWindowTitle("Serial Port Settings")
        self.setModal(True)
        try:
            self.setStyleSheet(_DLG_STYLE)
        except Exception:
            pass

        form = QGridLayout()
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(8)
        form.setContentsMargins(14, 12, 14, 12)

        def _label(text):
            lab = QLabel(text)
            lab.setStyleSheet("color:#cfd9ec;font-size:12px;background:transparent;border:none;")
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
            combo.setStyleSheet(
                "QComboBox{background:#091426;color:#e9eef7;border:1px solid #2b466f;"
                "border-radius:4px;padding:3px 6px;min-height:22px;}"
                "QComboBox:hover{border-color:#3a5a8a;}"
                "QComboBox:focus{border-color:#3a5a8a;}"
                "QComboBox QAbstractItemView{background:#091426;color:#e9eef7;"
                "selection-background-color:#162a4a;border:1px solid #2b466f;}"
            )

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
            warn = QLabel("⚠ Already connected. Changes apply to the next connection "
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

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addLayout(form)
        root.addWidget(btn_box)

        self.setMinimumWidth(320)

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


class SerialComMixin:
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    def init_serial_connection(self, mode=MODE_FULL, baudrate=115200, prefix="Serial"):
        from ui.modules.serialCom_module.serial_session_manager import SerialSessionManager
        self._serial_mode = mode
        self._serial_baudrate = baudrate
        self._serial_bytesize = 8
        self._serial_stopbits = serial.STOPBITS_ONE
        self._serial_parity = serial.PARITY_NONE
        self._serial_xonxoff = False
        self._serial_rtscts = False
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

        self._sc_session_manager = SerialSessionManager(parent=self)
        self._sc_sessions: dict[str, "SerialSession"] = self._sc_session_manager._sessions
        self._sc_active_session_id: str | None = None

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
            self.serial_label.setStyleSheet(inline_serial_label_style())
            row.addWidget(self.serial_label)

            self.serial_combo = SerialDarkComboBox()
            self.serial_combo.setSizeAdjustPolicy(
                SerialDarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
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
                self.serial_search_btn.styleSheet() + inline_serial_search_button_extra_style(_inline_h)
            )
            row.addWidget(self.serial_search_btn)

            layout.addLayout(row)
            return

        status_row = QHBoxLayout()
        status_row.setSpacing(6)
        status_row.setContentsMargins(0, 0, 0, 0)

        self.serial_status_label = QLabel("● Not Connected")
        self.serial_status_label.setObjectName("statusErr")
        status_row.addWidget(self.serial_status_label, 1)

        self.serial_settings_btn = QPushButton("⚙")
        self.serial_settings_btn.setToolTip("Serial port settings")
        self.serial_settings_btn.setFocusPolicy(Qt.NoFocus)
        self.serial_settings_btn.setCursor(Qt.PointingHandCursor)
        self.serial_settings_btn.setFixedSize(btn_height, btn_height)
        self.serial_settings_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:#8ea6cf;border:1px solid #2b466f;"
            f"border-radius:{btn_radius}px;font-size:13px;padding:0;}}"
            f"QPushButton:hover{{color:#e9eef7;border-color:#3a5a8a;background:#162a4a;}}"
            f"QPushButton:pressed{{background:#0f1f3a;}}"
            f"QPushButton:disabled{{color:#4a5b78;border-color:#1f3262;}}"
        )
        status_row.addWidget(self.serial_settings_btn, 0)

        layout.addLayout(status_row)

        self.serial_combo = SerialDarkComboBox()
        self.serial_combo.setSizeAdjustPolicy(
            SerialDarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
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
        if hasattr(self, 'serial_settings_btn'):
            self.serial_settings_btn.clicked.connect(self._on_serial_settings)

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
        thread = QThread(self)
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

            session_id = "primary"
            session = self._sc_session_manager.get_session(session_id)
            if session is None:
                session = self._sc_session_manager.create_session(
                    session_id=session_id, display_name=self._serial_prefix, auto_activate=True
                )
            session.configure(port=port, baudrate=br)
            session._serial_conn = conn
            session._connected = True
            self._sc_active_session_id = session_id

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

        session_id = "primary"
        session = self._sc_session_manager.get_session(session_id)
        if session is None:
            session = self._sc_session_manager.create_session(
                session_id=session_id, display_name=self._serial_prefix, auto_activate=True
            )
        session.configure(
            port=port,
            baudrate=self._serial_baudrate,
            bytesize=self._serial_bytesize,
            stopbits=self._serial_stopbits,
            parity=self._serial_parity,
            xonxoff=self._serial_xonxoff,
            rtscts=self._serial_rtscts,
        )

        if DEBUG_MOCK:
            self._serial_conn = None
            self._serial_port = "MOCK"
            self._serial_connected = True
            session._connected = True
            self._sc_active_session_id = session_id
            self._update_serial_connect_ui(True)
            self._set_serial_status(f"● Connected to: MOCK (DEBUG)")
            if hasattr(self, 'append_log'):
                self.append_log(f"[{self._serial_prefix}] Mock serial connected.")
            self.serial_connection_changed.emit(True)
            return

        self._set_serial_status("● Connecting")
        try:
            conn = serial.Serial(
                port,
                self._serial_baudrate,
                bytesize=self._serial_bytesize,
                stopbits=self._serial_stopbits,
                parity=self._serial_parity,
                xonxoff=self._serial_xonxoff,
                rtscts=self._serial_rtscts,
                timeout=1,
            )
            self._serial_conn = conn
            self._serial_port = port
            self._serial_connected = True
            session._serial_conn = conn
            session._connected = True
            self._sc_active_session_id = session_id
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
        session = self._sc_session_manager.get_session("primary")
        if session is not None:
            session._serial_conn = None
            session._connected = False
        self._update_serial_connect_ui(False)
        self._set_serial_status("● Not Connected", is_error=True)
        if hasattr(self, 'append_log'):
            self.append_log(f"[{self._serial_prefix}] Disconnected.")
        self.serial_connection_changed.emit(False)
        self.serial_connect_btn.setEnabled(True)

    def _on_serial_settings(self):
        dlg = _MixinSerialSettingsDialog(
            parent=self if isinstance(self, QWidget) else None,
            baudrate=self._serial_baudrate,
            bytesize=self._serial_bytesize,
            stopbits=self._serial_stopbits,
            parity=self._serial_parity,
            xonxoff=self._serial_xonxoff,
            rtscts=self._serial_rtscts,
            connected=self._serial_connected,
        )
        if dlg.exec() != QDialog.Accepted:
            return
        cfg = dlg.result_config()
        self._serial_baudrate = cfg["baudrate"]
        self._serial_bytesize = cfg["bytesize"]
        self._serial_stopbits = cfg["stopbits"]
        self._serial_parity = cfg["parity"]
        self._serial_xonxoff = cfg["xonxoff"]
        self._serial_rtscts = cfg["rtscts"]

        session = self._sc_session_manager.get_session("primary") \
            if hasattr(self, "_sc_session_manager") else None
        if session is not None:
            session.configure(
                port=session.port or (self._serial_port or ""),
                baudrate=self._serial_baudrate,
                bytesize=self._serial_bytesize,
                stopbits=self._serial_stopbits,
                parity=self._serial_parity,
                xonxoff=self._serial_xonxoff,
                rtscts=self._serial_rtscts,
            )

        if hasattr(self, "append_log"):
            self.append_log(
                f"[{self._serial_prefix}] Settings updated: "
                f"{self._serial_baudrate} {self._serial_bytesize}"
                f"{self._serial_parity}{self._serial_stopbits} "
                f"flow={'XON' if self._serial_xonxoff else ('RTS' if self._serial_rtscts else 'None')}"
            )

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
        if hasattr(self, 'serial_settings_btn'):
            self.serial_settings_btn.setEnabled(not connected)

    def _start_serial_read(self):
        if self._serial_conn is None or not self._serial_conn.is_open:
            return
        if self._serial_read_thread is not None and self._serial_read_thread.isRunning():
            return

        worker = _SerialReadWorker(self._serial_conn)
        thread = QThread(self)
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
        active = self._sc_session_manager.active_session
        if active is not None and active.connected:
            return active.send(data)
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

    def send_to_session(self, session_id: str, data) -> bool:
        return self._sc_session_manager.send_to_session(session_id, data)

    def send_to_active_session(self, data) -> bool:
        return self._sc_session_manager.send_to_active_session(data)

    def broadcast_send(self, data, session_ids=None) -> dict:
        return self._sc_session_manager.broadcast_send(data, session_ids)

    def get_serial_connection(self):
        active = self._sc_session_manager.active_session
        if active is not None:
            return active.serial_conn
        return self._serial_conn

    def is_serial_connected(self):
        active = self._sc_session_manager.active_session
        if active is not None:
            return active.connected
        return self._serial_connected

    def close_serial(self):
        if hasattr(self, "_sc_stop_ntp_sync"):
            self._sc_stop_ntp_sync()
        if getattr(self, "_sc_script_running", False):
            self._sc_script_stop()
        self._sc_session_manager.cleanup_all()
        self._stop_serial_read()
        if hasattr(self, '_sc_extra_log_panels'):
            for panel in self._sc_extra_log_panels:
                if panel.get("read_worker"):
                    panel["read_worker"].stop()
                if panel.get("read_thread") and panel["read_thread"].isRunning():
                    panel["read_thread"].quit()
                    panel["read_thread"].wait(2000)
                panel["read_thread"] = None
                panel["read_worker"] = None
                try:
                    if panel.get("conn") and panel["conn"].is_open:
                        panel["conn"].close()
                except Exception:
                    pass
                panel["conn"] = None
        if hasattr(self, '_sc_log_file_handle'):
            self._sc_stop_auto_save()
        if hasattr(self, '_sc_save_handle'):
            self._sc_stop_manual_save()
        if hasattr(self, '_sc_log_temp_handle'):
            self._sc_close_temp_log(delete=True)
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
        self._sc_log_auto_save = False
        self._sc_log_save_path = ''
        self._sc_log_file_handle = None
        self._sc_log_file_path = None
        self._sc_log_temp_handle = None
        self._sc_log_temp_path = None
        self._sc_save_handle = None
        self._sc_save_path = None
        self._sc_save_keep_timestamp = True
        self._sc_rx_display_hex = False
        self._sc_tx_display_hex = False
        self._sc_show_timestamp = True
        self._sc_use_ntp = False
        self._sc_ntp_offset = 0.0
        self._sc_ntp_synced = False
        self._sc_ntp_thread = None
        self._sc_ntp_worker = None
        self._sc_line_ending = "\r\n"
        self._sc_show_send = True
        self._sc_line_by_line = False
        self._sc_send_history = []
        self._sc_quick_commands = []  # 兼容占位，已不再使用
        self._sc_qc_data = self._sc_qc_default_data()
        self._sc_script_data = self._sc_script_default_data()
        self._sc_script_running = False
        self._sc_script_paused = False
        self._sc_script_steps = []
        self._sc_script_step_index = 0
        self._sc_script_loop_remaining = 0
        self._sc_script_wait_keyword = ""
        self._sc_script_wait_buffer = ""
        self._sc_script_timer = QTimer(self)
        self._sc_script_timer.setSingleShot(True)
        self._sc_script_timer.timeout.connect(self._sc_script_on_timeout)
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
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        self._sc_toolbar = self._build_sc_toolbar()
        outer.addWidget(self._sc_toolbar)

        body_splitter = QSplitter(Qt.Horizontal)
        body_splitter.setHandleWidth(10)
        body_splitter.setStyleSheet(body_splitter_style())

        self._sc_body_splitter = body_splitter
        self._sc_sidebar_default_width = 250
        self._sc_sidebar_min_width = 237
        self._sc_sidebar_widget = self._build_sc_sidebar()
        body_splitter.addWidget(self._sc_sidebar_widget)

        center_widget = QFrame()
        center_widget.setObjectName("scCenterWidget")
        center_widget.setFrameShape(QFrame.NoFrame)
        center_widget.setAutoFillBackground(True)
        center_widget.setStyleSheet(center_widget_style())
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(10, 10, 10, 10)
        center_layout.setSpacing(10)

        center_splitter = QSplitter(Qt.Vertical)
        center_splitter.setObjectName("scCenterVSplitter")
        center_splitter.setHandleWidth(6)
        center_splitter.setChildrenCollapsible(False)
        center_splitter.setStyleSheet(center_vsplitter_style())
        self._sc_center_splitter = center_splitter

        top_section = QWidget()
        top_section_layout = QVBoxLayout(top_section)
        top_section_layout.setContentsMargins(0, 0, 0, 0)
        top_section_layout.setSpacing(10)

        self._sc_log_container = QWidget()
        self._sc_log_grid = QGridLayout(self._sc_log_container)
        self._sc_log_grid.setContentsMargins(0, 0, 0, 0)
        self._sc_log_grid.setSpacing(10)

        self._sc_log_area = self._build_sc_log_area()
        self._sc_log_grid.addWidget(self._sc_log_area, 0, 0)
        top_section_layout.addWidget(self._sc_log_container, 1)

        self._sc_send_area = self._build_sc_send_area()
        top_section_layout.addWidget(self._sc_send_area)

        self._sc_quick_area = self._build_sc_quick_commands()
        self._sc_quick_area.setMinimumHeight(150)

        center_splitter.addWidget(top_section)
        center_splitter.addWidget(self._sc_quick_area)
        center_splitter.setStretchFactor(0, 1)
        center_splitter.setStretchFactor(1, 0)
        self._sc_center_splitter_default_sizes = [680, 155]
        center_splitter.setSizes(self._sc_center_splitter_default_sizes)

        self._sc_center_split_save_timer = QTimer(self)
        self._sc_center_split_save_timer.setSingleShot(True)
        self._sc_center_split_save_timer.setInterval(400)
        self._sc_center_split_save_timer.timeout.connect(self._sc_save_persisted_state)
        center_splitter.splitterMoved.connect(
            lambda *_: self._sc_center_split_save_timer.start()
        )

        center_layout.addWidget(center_splitter, 1)

        body_splitter.addWidget(center_widget)
        body_splitter.setStretchFactor(0, 0)
        body_splitter.setStretchFactor(1, 1)
        body_splitter.setSizes([self._sc_sidebar_default_width, 900])

        outer.addWidget(body_splitter, 1)

        parent_layout.addLayout(outer)

        self._bind_sc_signals()

        self._sc_pending_html = []
        self._sc_flush_timer = QTimer()
        self._sc_flush_timer.setInterval(100)
        self._sc_flush_timer.timeout.connect(self._sc_flush_pending_logs)
        self._sc_flush_timer.start()

        self._sc_load_persisted_state()
        self._sc_start_temp_log()

    # --- toolbar ---

    def _build_sc_toolbar(self):
        frame = QFrame()
        frame.setObjectName("scToolbar")
        frame.setFixedHeight(48)
        frame.setStyleSheet(toolbar_style())
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(8)

        self._sc_connect_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "connect.svg"), "Connect"
        )
        self._sc_connect_btn.setStyleSheet(toolbar_connect_button_style())
        icon_conn = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "connect.svg"), _CLR_CONNECT_TEXT, 13)
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

        layout.addSpacing(8)
        sep_conn = QFrame()
        sep_conn.setFrameShape(QFrame.VLine)
        sep_conn.setStyleSheet(separator_style())
        layout.addWidget(sep_conn)
        layout.addSpacing(8)

        self._sc_add_log_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "plus.svg"), ""
        )
        self._sc_add_log_btn.setFixedSize(28, 28)
        self._sc_add_log_btn.setToolTip("Add LOG panel")
        self._sc_add_log_btn.setStyleSheet(log_panel_button_style())
        icon_add = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "plus.svg"), _CLR_CONNECT_TEXT, 14)
        if not icon_add.isNull():
            self._sc_add_log_btn.setIcon(icon_add)
        layout.addWidget(self._sc_add_log_btn)

        self._sc_remove_log_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "minus.svg"), ""
        )
        self._sc_remove_log_btn.setFixedSize(28, 28)
        self._sc_remove_log_btn.setToolTip("Remove current LOG panel")
        self._sc_remove_log_btn.setStyleSheet(log_panel_button_style(disabled=True))
        icon_remove = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "minus.svg"), _CLR_ROSE_ICON, 14)
        if not icon_remove.isNull():
            self._sc_remove_log_btn.setIcon(icon_remove)
        self._sc_remove_log_btn.setEnabled(False)
        layout.addWidget(self._sc_remove_log_btn)

        layout.addSpacing(8)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(separator_style())
        layout.addWidget(sep)

        layout.addSpacing(8)

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
        wrapper = QFrame()
        wrapper.setObjectName("scSidebarWrapper")
        wrapper.setMinimumWidth(self._sc_sidebar_min_width)
        wrapper.setMaximumWidth(298)
        wrapper.setStyleSheet(sidebar_wrapper_style())
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(transparent_scroll_area_style())

        vbar = scroll.verticalScrollBar()
        vbar.setFixedWidth(4)
        vbar.setStyleSheet(thin_scrollbar_style())

        container = QWidget()
        root = QVBoxLayout(container)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        root.addWidget(self._build_sc_section_port_settings())
        root.addWidget(self._build_sc_section_rx_settings())
        root.addWidget(self._build_sc_section_tx_settings())
        root.addStretch()

        scroll.setWidget(container)
        wrapper_layout.addWidget(scroll)
        return wrapper

    def _build_sc_section_port_settings(self):
        grp = self._make_sc_section("Serial Config")
        layout = grp.property("_inner_layout")

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)
        grid.setColumnMinimumWidth(0, 66)
        grid.setColumnStretch(1, 1)

        grid.addWidget(self._make_sc_label("Port"), 0, 0)
        self._sc_port_combo = SerialDarkComboBox()
        self._sc_port_combo.setFixedHeight(28)
        self._sc_port_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self._sc_port_combo.setMinimumWidth(60)
        f = self._sc_port_combo.font()
        f.setPixelSize(12)
        self._sc_port_combo.setFont(f)
        grid.addWidget(self._sc_port_combo, 0, 1)

        grid.addWidget(self._make_sc_label("Baudrate"), 1, 0)
        self._sc_baud_combo = SerialDarkComboBox()
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
        self._sc_databit_combo = SerialDarkComboBox()
        self._sc_databit_combo.setFixedHeight(28)
        for d in ["8", "7", "6", "5"]:
            self._sc_databit_combo.addItem(d)
        grid.addWidget(self._sc_databit_combo, 3, 1)

        grid.addWidget(self._make_sc_label("Flow Control"), 4, 0)
        self._sc_flow_combo = SerialDarkComboBox()
        self._sc_flow_combo.setFixedHeight(28)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._sc_flow_combo.addItem(fc)
        grid.addWidget(self._sc_flow_combo, 4, 1)

        grid.addWidget(self._make_sc_label("Stop bits"), 5, 0)
        self._sc_stopbit_combo = SerialDarkComboBox()
        self._sc_stopbit_combo.setFixedHeight(28)
        for s in ["1", "1.5", "2"]:
            self._sc_stopbit_combo.addItem(s)
        grid.addWidget(self._sc_stopbit_combo, 5, 1)

        grid.addWidget(self._make_sc_label("Parity"), 6, 0)
        self._sc_parity_combo = SerialDarkComboBox()
        self._sc_parity_combo.setFixedHeight(28)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._sc_parity_combo.addItem(p)
        grid.addWidget(self._sc_parity_combo, 6, 1)

        layout.addLayout(grid)
        return grp

    _TOGGLE_W = 92
    _SPIN_W = _TOGGLE_W // 2
    _INTERVAL_SPIN_W = _TOGGLE_W
    _MS_LABEL_W = 16
    _COMBO_END_W = _TOGGLE_W

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
        self._sc_rx_auto_flush_spin.setSuffix(" ms")
        self._sc_rx_auto_flush_spin.setAlignment(Qt.AlignCenter)
        self._sc_rx_auto_flush_spin.setFixedSize(self._INTERVAL_SPIN_W, 26)
        self._sc_rx_auto_flush_spin.setStyleSheet(
            compact_spinbox_style(up_button_width=0, padding="2px 8px")
        )
        row_af.addWidget(self._sc_rx_auto_flush_spin)
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

        row_ending = QHBoxLayout()
        row_ending.setSpacing(4)
        row_ending.addWidget(self._make_sc_label("Line Ending"))
        row_ending.addStretch()
        self._sc_ending_combo = SerialDarkComboBox()
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
        frame.setStyleSheet(log_frame_style())
        frame.setProperty("_is_primary", True)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(12, 10, 12, 8)
        toolbar.setSpacing(8)

        icon_label = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "logs.svg"), _CLR_TEXT_BTN_LOG, 12)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(12, 12))
        icon_label.setFixedSize(14, 14)
        icon_label.setStyleSheet(transparent_background_style())
        toolbar.addWidget(icon_label)

        title = QLabel("Serial Log")
        title.setStyleSheet(log_title_style())
        toolbar.addWidget(title)

        toolbar.addStretch()

        self._sc_filter_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "filter.svg"), "Filter", tone="log"
        )
        self._sc_filter_btn.setCheckable(True)
        self._sc_filter_btn.setStyleSheet(log_toolbar_button_style(checked_variant=True))
        toolbar.addWidget(self._sc_filter_btn)

        self._sc_copy_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "copy.svg"), "Copy", tone="log"
        )
        toolbar.addWidget(self._sc_copy_btn)

        self._sc_export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export", tone="log"
        )
        toolbar.addWidget(self._sc_export_btn)

        self._sc_save_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "save.svg"), "Save", tone="log"
        )
        self._sc_save_btn.setCheckable(True)
        self._sc_save_btn.setStyleSheet(log_toolbar_button_style(checked_variant=True))
        self._sc_save_btn.setToolTip("Save logs to a file and keep appending new logs")
        toolbar.addWidget(self._sc_save_btn)

        self._sc_clear_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), "Clear", tone="log"
        )
        toolbar.addWidget(self._sc_clear_btn)

        self._sc_scroll_lock_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"), "Auto-scroll", tone="log"
        )
        self._sc_scroll_lock_btn.setCheckable(True)
        self._sc_scroll_lock_btn.setChecked(True)
        self._sc_scroll_lock_btn.setStyleSheet(log_toolbar_button_style(checked_variant=True))
        toolbar.addWidget(self._sc_scroll_lock_btn)

        layout.addLayout(toolbar)

        self._sc_filter_row = QWidget()
        self._sc_filter_row.setVisible(False)
        self._sc_filter_row.setStyleSheet(transparent_background_style())
        filter_root = QVBoxLayout(self._sc_filter_row)
        filter_root.setContentsMargins(12, 0, 12, 8)
        filter_root.setSpacing(6)

        fl = QHBoxLayout()
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(8)
        self._sc_filter_input = QLineEdit()
        self._sc_filter_input.setPlaceholderText("Enter keyword or regex, press Enter to filter...")
        self._sc_filter_input.setStyleSheet(filter_input_style())
        fl.addWidget(self._sc_filter_input, 1)

        self._sc_filter_match_label = QLabel("")
        self._sc_filter_match_label.setStyleSheet(filter_match_label_style())
        fl.addWidget(self._sc_filter_match_label)
        filter_root.addLayout(fl)

        opts = QHBoxLayout()
        opts.setContentsMargins(0, 0, 0, 0)
        opts.setSpacing(10)

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
        sep.setStyleSheet(separator_style(transparent=True))
        opts.addWidget(sep)

        opts.addSpacing(4)

        before_lbl = QLabel("Before")
        before_lbl.setStyleSheet(small_label_style())
        opts.addWidget(before_lbl)
        self._sc_filter_before_spin = QSpinBox()
        self._sc_filter_before_spin.setRange(0, 999)
        self._sc_filter_before_spin.setValue(0)
        self._sc_filter_before_spin.setFixedSize(56, 24)
        self._sc_filter_before_spin.setToolTip("Show N lines before matched lines")
        self._sc_filter_before_spin.setStyleSheet(compact_spinbox_style(padding="0px 2px"))
        opts.addWidget(self._sc_filter_before_spin)
        before_unit = QLabel("lines")
        before_unit.setStyleSheet(small_label_style(size=11))
        opts.addWidget(before_unit)

        opts.addSpacing(4)

        after_lbl = QLabel("After")
        after_lbl.setStyleSheet(small_label_style())
        opts.addWidget(after_lbl)
        self._sc_filter_after_spin = QSpinBox()
        self._sc_filter_after_spin.setRange(0, 999)
        self._sc_filter_after_spin.setValue(0)
        self._sc_filter_after_spin.setFixedSize(56, 24)
        self._sc_filter_after_spin.setToolTip("Show N lines after matched lines")
        self._sc_filter_after_spin.setStyleSheet(compact_spinbox_style(padding="0px 2px"))
        opts.addWidget(self._sc_filter_after_spin)
        after_unit = QLabel("lines")
        after_unit.setStyleSheet(small_label_style(size=11))
        opts.addWidget(after_unit)

        opts.addStretch()
        filter_root.addLayout(opts)

        layout.addWidget(self._sc_filter_row)

        self._sc_log_edit = QTextEdit()
        self._sc_log_edit.setReadOnly(True)
        self._sc_log_edit.setStyleSheet(log_edit_style() + SERIAL_SCROLLBAR_STYLE)
        self._sc_log_edit.document().setDefaultStyleSheet(log_document_style())
        self._sc_log_edit.document().setMaximumBlockCount(5000)
        layout.addWidget(self._sc_log_edit, 1)

        if self._sc_log_edit.verticalScrollBar():
            self._sc_log_edit.verticalScrollBar().valueChanged.connect(self._sc_on_user_scroll)

        self._sc_status_bar = self._build_sc_status_bar()
        layout.addWidget(self._sc_status_bar)

        frame.mousePressEvent = lambda event: self._sc_on_primary_panel_clicked(event)
        self._sc_log_edit.mousePressEvent = lambda event, orig=self._sc_log_edit.mousePressEvent: (
            self._sc_on_primary_panel_clicked(event), orig(event)
        )

        return frame

    # --- send area ---

    def _build_sc_send_area(self):
        widget = QWidget()
        widget.setStyleSheet(transparent_background_style())
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        send_row = QHBoxLayout()
        send_row.setContentsMargins(0, 0, 0, 0)
        send_row.setSpacing(8)

        self._sc_history_combo = SerialDarkComboBox()
        self._sc_history_combo.setEditable(True)
        self._sc_history_combo.setInsertPolicy(SerialDarkComboBox.NoInsert)
        self._sc_history_combo.setFixedHeight(34)
        self._sc_send_input = self._sc_history_combo.lineEdit()
        self._sc_send_input.setPlaceholderText("Enter text to send (\u2193 for history)...")
        self._sc_send_input.setClearButtonEnabled(False)
        self._sc_history_combo.setStyleSheet(history_combo_style())
        send_row.addWidget(self._sc_history_combo, 1)

        self._sc_send_btn = QPushButton("Send")
        self._sc_send_btn.setCursor(Qt.PointingHandCursor)
        self._sc_send_btn.setFixedHeight(34)
        self._sc_send_btn.setMinimumWidth(92)
        icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "send.svg"), _CLR_BG_MAIN, 11)
        if not icon.isNull():
            self._sc_send_btn.setIcon(icon)
        self._sc_send_btn.setStyleSheet(send_button_style())
        send_row.addWidget(self._sc_send_btn)

        layout.addLayout(send_row)

        return widget

    # --- quick commands ---

    def _build_sc_quick_commands(self):
        tabs = QTabWidget()
        tabs.setObjectName("scBottomTabs")
        tabs.setDocumentMode(True)
        tabs.setStyleSheet(bottom_tabs_style())
        tabs.tabBar().setCursor(Qt.PointingHandCursor)
        self._sc_bottom_tabs = tabs

        qc_icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "zap.svg"), _CLR_TEXT_MUTED, 13)
        script_icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "logs.svg"), _CLR_TEXT_MUTED, 13)

        qc_index = tabs.addTab(self._build_sc_qc_tab(), "Quick Commands")
        script_index = tabs.addTab(self._build_sc_script_tab(), "Scripts")
        if not qc_icon.isNull():
            tabs.setTabIcon(qc_index, qc_icon)
        if not script_icon.isNull():
            tabs.setTabIcon(script_index, script_icon)
        tabs.setIconSize(QSize(13, 13))
        return tabs

    def _build_sc_qc_tab(self):
        frame = QFrame()
        # 双 objectName 不可行：保留 scQuickFrame 给现有内嵌 QSS；面板级 QSS 通过 quickCommandsPanel 选择器命中
        frame.setObjectName("quickCommandsPanel")
        frame.setProperty("class", "scQuickFrame")
        # 外层面板 + 内部分隔条：背景柔和、低对比边框、圆角；不改变布局
        # 置于 scBottomTabs 的 pane 内，外框由 pane 提供，内层面板去边框避免双边框
        frame.setStyleSheet(quick_commands_panel_style() + "QFrame#quickCommandsPanel { border: none; background: transparent; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- header: 标题 + 项目 Tab 栏 ---
        header_frame = QFrame()
        header_frame.setObjectName("scQuickHeaderFrame")
        header_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        header = QHBoxLayout(header_frame)
        header.setContentsMargins(10, 8, 10, 0)
        header.setSpacing(6)

        zap_icon = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "zap.svg"), _CLR_WARN_ICON, 10)
        if not icon.isNull():
            zap_icon.setPixmap(icon.pixmap(10, 10))
        zap_icon.setFixedSize(10, 10)
        zap_icon.setStyleSheet(transparent_background_style())
        header.addWidget(zap_icon)

        lbl = QLabel("Quick Commands")
        lbl.setObjectName("quickCommandsTitle")
        # 颜色 / 字号由面板级 QSS (#quickCommandsTitle) 接管，此处仅设置背景透明以避免被父容器覆盖
        lbl.setStyleSheet(transparent_background_style())
        header.addWidget(lbl)

        # 项目 Tab 栏（最顶层分组），末尾内置 "+" 加号 tab，右键菜单 + 拖拽排序
        self._sc_qc_project_tabs = _ProjectTabBar()
        self._sc_qc_project_tabs.setExpanding(False)
        self._sc_qc_project_tabs.setDrawBase(False)
        self._sc_qc_project_tabs.setUsesScrollButtons(True)
        self._sc_qc_project_tabs.setStyleSheet(project_tabs_style())
        self._sc_qc_project_tabs.setMinimumHeight(24)
        self._sc_qc_project_tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        header.addWidget(self._sc_qc_project_tabs, 1)

        layout.addWidget(header_frame)

        # --- 工具栏:区域/分组下拉 + 操作按钮 ---
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("scQuickToolbar")
        toolbar_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(6)

        _combo_qss = quick_combo_style()

        group_lbl = QLabel("Group:")
        group_lbl.setStyleSheet(small_label_style(color="soft", size=11))
        toolbar.addWidget(group_lbl)
        self._sc_qc_group_combo = QComboBox()
        self._sc_qc_group_combo.setStyleSheet(_combo_qss)
        self._sc_qc_group_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        toolbar.addWidget(self._sc_qc_group_combo)

        self._sc_qc_new_group_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "plus.svg"), "Group", tone="quick"
        )
        # 工具栏统一暗色按钮样式：覆盖 _make_sc_btn(quick) 的局部 setStyleSheet
        _toolbar_btn_qss = quick_toolbar_button_style()
        self._sc_qc_new_group_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_qc_new_group_btn)

        toolbar.addStretch()

        self._sc_qc_add_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "plus.svg"), "Add", tone="quick"
        )
        # + Add 作为主操作按钮：蓝色突出
        self._sc_qc_add_btn.setObjectName("primaryButton")
        self._sc_qc_add_btn.setStyleSheet(quick_add_button_style())
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
        self._sc_qc_btn_scroll.setStyleSheet(quick_button_scroll_style() + SERIAL_SCROLLBAR_STYLE)
        self._sc_qc_btn_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._sc_qc_btn_scroll.setMinimumHeight(44)
        self._sc_qc_btn_scroll.setMaximumHeight(126)
        self._sc_qc_btn_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._sc_qc_btn_container = QWidget()
        self._sc_qc_btn_container.setObjectName("scQuickBtnContainer")
        self._sc_qc_btn_container.setStyleSheet(quick_button_container_style())
        # 接受拖拽：本控件作为快捷指令按钮的统一 drop 目标，事件经 eventFilter 派发
        self._sc_qc_btn_container.setAcceptDrops(True)
        self._sc_qc_btn_container.installEventFilter(self)
        self._sc_qc_btn_layout = QGridLayout(self._sc_qc_btn_container)
        self._sc_qc_btn_layout.setContentsMargins(10, 10, 10, 10)
        self._sc_qc_btn_layout.setHorizontalSpacing(8)
        self._sc_qc_btn_layout.setVerticalSpacing(8)

        self._sc_qc_btn_scroll.setWidget(self._sc_qc_btn_container)
        layout.addWidget(self._sc_qc_btn_scroll)

        return frame

    # --- scripts ---

    def _build_sc_script_tab(self):
        frame = QFrame()
        frame.setObjectName("quickCommandsPanel")
        frame.setProperty("class", "scQuickFrame")
        # 置于 scBottomTabs 的 pane 内，外框由 pane 提供，内层面板去边框避免双边框
        frame.setStyleSheet(quick_commands_panel_style() + "QFrame#quickCommandsPanel { border: none; background: transparent; }")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- 工具栏：脚本选择 + 运行控制 ---
        toolbar_frame = QFrame()
        toolbar_frame.setObjectName("scQuickToolbar")
        toolbar = QHBoxLayout(toolbar_frame)
        toolbar.setContentsMargins(10, 8, 10, 8)
        toolbar.setSpacing(6)

        _combo_qss = quick_combo_style()
        _toolbar_btn_qss = quick_toolbar_button_style()

        script_lbl = QLabel("Script:")
        script_lbl.setStyleSheet(small_label_style(color="soft", size=11))
        toolbar.addWidget(script_lbl)

        self._sc_script_combo = QComboBox()
        self._sc_script_combo.setStyleSheet(_combo_qss)
        self._sc_script_combo.setMinimumWidth(160)
        toolbar.addWidget(self._sc_script_combo)

        self._sc_script_run_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "send.svg"), "Run", tone="quick"
        )
        self._sc_script_run_btn.setObjectName("primaryButton")
        self._sc_script_run_btn.setStyleSheet(quick_add_button_style())
        toolbar.addWidget(self._sc_script_run_btn)

        self._sc_script_stop_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "stop.svg"), "Stop", tone="quick"
        )
        self._sc_script_stop_btn.setStyleSheet(_toolbar_btn_qss)
        self._sc_script_stop_btn.setEnabled(False)
        toolbar.addWidget(self._sc_script_stop_btn)

        toolbar.addSpacing(8)
        self._sc_script_loop_cb = QCheckBox("Loop")
        self._sc_script_loop_cb.setStyleSheet(self._sc_checkbox_style())
        self._sc_script_loop_cb.setToolTip("Repeat the script for the configured number of times")
        toolbar.addWidget(self._sc_script_loop_cb)

        self._sc_script_loop_spin = QSpinBox()
        self._sc_script_loop_spin.setObjectName("scIntervalSpin")
        self._sc_script_loop_spin.setRange(1, 99999)
        self._sc_script_loop_spin.setValue(1)
        self._sc_script_loop_spin.setFixedWidth(self._INTERVAL_SPIN_W)
        self._sc_script_loop_spin.setToolTip("Number of times to repeat the script")
        self._sc_script_loop_spin.setStyleSheet(quick_combo_style())
        toolbar.addWidget(self._sc_script_loop_spin)

        toolbar.addStretch()

        self._sc_script_new_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "plus.svg"), "New", tone="quick"
        )
        self._sc_script_new_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_script_new_btn)

        self._sc_script_edit_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "settings.svg"), "Edit", tone="quick"
        )
        self._sc_script_edit_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_script_edit_btn)

        self._sc_script_del_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), "Delete", tone="quick"
        )
        self._sc_script_del_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_script_del_btn)

        self._sc_script_import_btn = self._make_sc_btn(
            os.path.join(_SVG_SERIAL_DIR, "import.svg"), "Import", tone="quick"
        )
        self._sc_script_import_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_script_import_btn)

        self._sc_script_export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export", tone="quick"
        )
        self._sc_script_export_btn.setStyleSheet(_toolbar_btn_qss)
        toolbar.addWidget(self._sc_script_export_btn)

        layout.addWidget(toolbar_frame)

        # --- 状态栏 ---
        status_frame = QFrame()
        status_frame.setObjectName("scQuickToolbar")
        status_row = QHBoxLayout(status_frame)
        status_row.setContentsMargins(10, 0, 10, 6)
        status_row.setSpacing(6)
        self._sc_script_status_label = QLabel("\u2022 Idle")
        self._sc_script_status_label.setStyleSheet(status_label_style("muted", include_font=True))
        status_row.addWidget(self._sc_script_status_label)
        status_row.addStretch()
        layout.addWidget(status_frame)

        # --- 步骤预览表 ---
        self._sc_script_table = QTableWidget(0, 5)
        self._sc_script_table.setHorizontalHeaderLabels(
            ["#", "Command", "Priority", "Wait (ms)", "Status"]
        )
        self._sc_script_table.verticalHeader().setVisible(False)
        self._sc_script_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._sc_script_table.setSelectionMode(QAbstractItemView.NoSelection)
        self._sc_script_table.setFocusPolicy(Qt.NoFocus)
        self._sc_script_table.setStyleSheet(self._sc_script_table_qss() + SERIAL_SCROLLBAR_STYLE)
        self._sc_script_table.setMinimumHeight(54)
        self._sc_script_table.setMaximumHeight(160)
        hdr = self._sc_script_table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        layout.addWidget(self._sc_script_table)

        self._sc_script_combo.currentIndexChanged.connect(self._sc_script_on_combo_changed)
        self._sc_script_run_btn.clicked.connect(self._sc_script_run)
        self._sc_script_stop_btn.clicked.connect(self._sc_script_stop)
        self._sc_script_loop_cb.toggled.connect(self._sc_script_on_loop_toggled)
        self._sc_script_loop_spin.valueChanged.connect(self._sc_script_on_loop_count_changed)
        self._sc_script_new_btn.clicked.connect(self._sc_script_new)
        self._sc_script_edit_btn.clicked.connect(self._sc_script_edit)
        self._sc_script_del_btn.clicked.connect(self._sc_script_delete)
        self._sc_script_import_btn.clicked.connect(self._sc_script_import_txt)
        self._sc_script_export_btn.clicked.connect(self._sc_script_export_txt)

        QTimer.singleShot(0, self._sc_script_refresh_all)
        return frame

    # --- status bar ---

    def _build_sc_status_bar(self):
        frame = QFrame()
        frame.setObjectName("scStatusBar")
        frame.setFixedHeight(32)
        frame.setStyleSheet(status_bar_style())
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 3, 12, 3)
        layout.setSpacing(18)

        self._sc_status_port_label = QLabel("\u2022 Port: Unconnected")
        self._sc_status_port_label.setStyleSheet(status_label_style("error", compact=True))
        layout.addWidget(self._sc_status_port_label)

        self._sc_status_baud_label = QLabel("Baud rate (bps): -")
        self._sc_status_baud_label.setStyleSheet(status_label_style("muted", compact=True))
        layout.addWidget(self._sc_status_baud_label)

        self._sc_status_rx_label = QLabel("RX: 0 B")
        self._sc_status_rx_label.setStyleSheet(status_label_style("rx", compact=True))
        layout.addWidget(self._sc_status_rx_label)

        self._sc_status_tx_label = QLabel("TX: 0 B")
        self._sc_status_tx_label.setStyleSheet(status_label_style("tx", compact=True))
        layout.addWidget(self._sc_status_tx_label)

        self._sc_status_autobaud_label = QLabel("")
        self._sc_status_autobaud_label.setStyleSheet(status_label_style("accent", compact=True))
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
        self._sc_save_btn.clicked.connect(self._sc_on_save_toggle)
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
            self._sc_append_system("[ERROR] No valid port selected", force_primary=True)
            return

        port = port_text.split()[0]

        baud_text = self._sc_baud_combo.currentText().strip()
        try:
            baudrate = int(baud_text)
        except ValueError:
            self._sc_append_system(f"[ERROR] Invalid baud rate: {baud_text}", force_primary=True)
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

        session_id = "primary"
        session = self._sc_session_manager.get_session(session_id)
        if session is None:
            session = self._sc_session_manager.create_session(
                session_id=session_id, display_name=self._serial_prefix, auto_activate=True
            )
        session.configure(
            port=port, baudrate=baudrate, bytesize=databit,
            stopbits=stopbits, parity=parity, xonxoff=xonxoff, rtscts=rtscts,
        )

        if DEBUG_MOCK:
            self._serial_conn = None
            self._serial_port = "MOCK"
            self._serial_baudrate = baudrate
            self._serial_connected = True
            session._connected = True
            self._sc_active_session_id = session_id
            self._sc_update_connect_ui(True)
            self._sc_start_temp_log()
            self._sc_append_system(f"[INFO] Mock connected: {port} @ {baudrate}", force_primary=True)
            self.serial_connection_changed.emit(True)
            if getattr(self, '_sc_log_auto_save', False):
                self._sc_start_auto_save()
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
            session._serial_conn = conn
            session._connected = True
            self._sc_active_session_id = session_id
            self._sc_update_connect_ui(True)
            self._sc_start_temp_log()
            self._sc_append_system(f"[INFO] Connected: {port} @ {baudrate}", force_primary=True)
            self.serial_connection_changed.emit(True)
            if getattr(self, '_sc_log_auto_save', False):
                self._sc_start_auto_save()
            if self._sc_auto_detect_cb.isChecked():
                self._sc_auto_baud_monitor.enabled = True
                self._sc_auto_baud_monitor.runtime_redetect_enabled = True
                self._sc_auto_baud_pending_first_rx = True
                self._sc_auto_baud_initial_buf = bytearray()
                self._sc_auto_baud_initial_ts = time.perf_counter()
                self._sc_append_system("[INFO] Auto-detect enabled, waiting for RX data...", force_primary=True)
            self._start_serial_read()
        except Exception as e:
            self._sc_append_system(f"[ERROR] Connection failed: {e}", force_primary=True)

    def _sc_do_disconnect(self):
        self._stop_serial_read()
        self._sc_stop_auto_baud_scan()
        self._sc_stop_auto_save()
        self._sc_close_temp_log(delete=True)
        try:
            if self._serial_conn and self._serial_conn.is_open:
                self._serial_conn.close()
        except Exception as e:
            self._sc_append_system(f"[WARN] Close error: {e}", force_primary=True)
        self._serial_conn = None
        self._serial_port = None
        self._serial_connected = False
        session = self._sc_session_manager.get_session("primary")
        if session is not None:
            session._serial_conn = None
            session._connected = False
        self._sc_update_connect_ui(False)
        self._sc_append_system("[INFO] Disconnected", force_primary=True)
        self.serial_connection_changed.emit(False)

    def _sc_update_connect_ui(self, connected):
        if not hasattr(self, '_sc_connect_btn_fixed_width_applied'):
            self._sc_connect_btn.setFixedWidth(96)
            self._sc_connect_btn_fixed_width_applied = True
        if connected:
            self._sc_connect_btn.setText("Disconnect")
            self._sc_connect_btn.setStyleSheet(main_connect_button_style(connected=True))
            icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "disconnect.svg"), _CLR_DISCONNECT_TEXT, 12)
            if not icon.isNull():
                self._sc_connect_btn.setIcon(icon)
            self._sc_status_port_label.setText(f"\u2022 Port: {self._serial_port}")
            self._sc_status_port_label.setStyleSheet(status_label_style("ok", include_font=True))
            baud = getattr(self, '_serial_baudrate', '-')
            self._sc_status_baud_label.setText(f"Baud rate (bps): {baud}")
        else:
            self._sc_connect_btn.setText("Connect")
            self._sc_connect_btn.setStyleSheet(main_connect_button_style(connected=False))
            icon = _tinted_svg_icon(os.path.join(_SVG_SERIAL_DIR, "connect.svg"), _CLR_CONNECT_TEXT, 12)
            if not icon.isNull():
                self._sc_connect_btn.setIcon(icon)
            self._sc_status_port_label.setText("\u2022 Port: Unconnected")
            self._sc_status_port_label.setStyleSheet(status_label_style("error", include_font=True))
            self._sc_status_baud_label.setText("Baud rate (bps): -")

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
                self._sc_append_system(f"[ERROR] Invalid baud rate: {baud_text}", force_primary=True)
            return

        if baudrate == getattr(self, '_serial_baudrate', None):
            return

        if not self._serial_connected:
            self._serial_baudrate = baudrate
            return

        if DEBUG_MOCK or self._serial_conn is None:
            self._serial_baudrate = baudrate
            if hasattr(self, '_sc_status_baud_label'):
                self._sc_status_baud_label.setText(f"Baud rate (bps): {baudrate}")
            self._sc_append_system(f"[INFO] Baud rate updated: {baudrate}", force_primary=True)
            return

        try:
            self._serial_conn.baudrate = baudrate
            self._serial_baudrate = baudrate
            if hasattr(self, '_sc_status_baud_label'):
                self._sc_status_baud_label.setText(f"Baud rate (bps): {baudrate}")
            self._sc_append_system(f"[INFO] Baud rate updated: {baudrate}", force_primary=True)
        except Exception as e:
            self._sc_append_system(f"[ERROR] Failed to set baud rate: {e}", force_primary=True)

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
                self._sc_append_system("[INFO] Auto-detect enabled, waiting for RX data...", force_primary=True)
        else:
            self._sc_status_autobaud_label.setVisible(False)
            self._sc_auto_baud_monitor.reset()
            self._sc_auto_baud_monitor.state = AutoBaudState.UNKNOWN
            self._sc_stop_auto_baud_scan()
            self._sc_auto_baud_pending_first_rx = False

    def _sc_start_auto_baud_scan(self, reason="initial"):
        if self._serial_conn is None or not self._serial_conn.is_open:
            self._sc_append_system("[WARN] Cannot auto-detect: serial not connected", force_primary=True)
            return
        if self._sc_auto_baud_scan_thread is not None and self._sc_auto_baud_scan_thread.isRunning():
            return

        self._stop_serial_read()

        config = dict(AUTO_BAUD_CONFIG)
        worker = AutoBaudScanWorker(
            self._serial_conn, config, self._serial_baudrate
        )
        worker.set_recent_score_avg(self._sc_auto_baud_monitor.recent_score_avg)
        thread = QThread(self)
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
                        f"[WARN] No baudrate scored above threshold. Best: {best['baudrate']} score={best['score']}",
                        force_primary=True,
                    )
            self._sc_auto_baud_monitor.state = AutoBaudState.LOCKED
            self._sc_auto_baud_monitor.reset()

    def _sc_on_auto_baud_progress(self, msg):
        self._sc_append_system(msg, force_primary=True)

    def _sc_on_auto_baud_state_changed(self, state_str):
        self._sc_auto_baud_monitor.state = AutoBaudState(state_str)
        label = self._sc_status_autobaud_label
        if state_str == AutoBaudState.SCANNING.value:
            label.setText("AutoBaud: SCANNING")
            label.setStyleSheet(status_label_style("warn"))
        elif state_str == AutoBaudState.SUSPECT.value:
            label.setText("AutoBaud: SUSPECT")
            label.setStyleSheet(status_label_style("error"))
        elif state_str == AutoBaudState.LOCKED.value:
            label.setText("AutoBaud: LOCKED")
            label.setStyleSheet(status_label_style("accent"))
        else:
            label.setText(f"AutoBaud: {state_str}")
            label.setStyleSheet(status_label_style("muted"))

    def _sc_on_auto_baud_baudrate_changed(self, baudrate):
        self._serial_baudrate = baudrate
        self._sc_baud_combo.setCurrentText(str(baudrate))
        if hasattr(self, '_sc_status_baud_label'):
            self._sc_status_baud_label.setText(f"Baud rate (bps): {baudrate}")

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
            self._sc_append_system("[INFO] Mock port refreshed", force_primary=True)
            self._sc_try_restore_last_port()
            return
        try:
            ports = serial.tools.list_ports.comports()
            if ports:
                for p in ports:
                    self._sc_port_combo.addItem(f"{p.device} - {p.description}")
                self._sc_append_system(f"[INFO] Found {len(ports)} serial port(s)", force_primary=True)
            else:
                self._sc_port_combo.addItem("No serial ports found")
                self._sc_append_system("[WARN] No serial ports found", force_primary=True)
        except Exception as e:
            self._sc_append_system(f"[ERROR] Refresh failed: {e}", force_primary=True)
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
            self._sc_append_system("[WARN] Maximum 4 LOG panels supported", force_primary=True)
            return
        dlg = _AddLogPanelDialog(panel_index=len(self._sc_extra_log_panels) + 2, parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        panel_info = dlg.get_config()

        if panel_info.get("independent_window", False):
            self._sc_open_independent_window(panel_info)
            return

        panel = self._build_extra_log_panel(panel_info)
        self._sc_extra_log_panels.append(panel)
        self._sc_relayout_log_panels()
        self._sc_remove_log_btn.setEnabled(True)
        self._sc_append_system(
            f"[INFO] New LOG panel: {panel_info.get('title', 'Log')} "
            f"({panel_info.get('port', 'N/A')} @ {panel_info.get('baudrate', 'N/A')})",
            force_primary=True,
        )
        if panel_info.get("auto_connect", False):
            self._sc_extra_panel_connect(panel)

    def _sc_open_independent_window(self, panel_info):
        win = _IndependentSerialWindow(panel_info, parent=None)
        if not hasattr(self, "_sc_independent_windows"):
            self._sc_independent_windows = []
        self._sc_independent_windows.append(win)
        win.setAttribute(Qt.WA_DeleteOnClose)
        win.destroyed.connect(lambda: self._sc_independent_windows.remove(win) if win in self._sc_independent_windows else None)
        win.show()
        self._sc_append_system(
            f"[INFO] Independent window opened: {panel_info.get('title', 'Log')} "
            f"({panel_info.get('port', 'N/A')} @ {panel_info.get('baudrate', 'N/A')})",
            force_primary=True,
        )

    def _sc_on_remove_log_panel(self):
        if not self._sc_extra_log_panels:
            return
        panel = self._sc_extra_log_panels.pop()
        self._sc_extra_panel_disconnect(panel)
        panel["frame"].setParent(None)
        panel["frame"].deleteLater()
        self._sc_relayout_log_panels()
        self._sc_remove_log_btn.setEnabled(len(self._sc_extra_log_panels) > 0)
        self._sc_append_system("[INFO] LOG panel removed", force_primary=True)

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
        frame.setStyleSheet(log_frame_style(with_border=True))
        frame.setContextMenuPolicy(Qt.CustomContextMenu)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(6, 4, 6, 2)
        toolbar.setSpacing(4)

        icon_label = QLabel()
        icon = _tinted_svg_icon(os.path.join(_SVG_LOGS_DIR, "logs.svg"), _CLR_TEXT_BTN_LOG, 12)
        if not icon.isNull():
            icon_label.setPixmap(icon.pixmap(12, 12))
        icon_label.setFixedSize(14, 14)
        icon_label.setStyleSheet(transparent_background_style())
        toolbar.addWidget(icon_label)

        title_text = config.get("title", "Serial Log")
        title = QLabel(title_text)
        title.setStyleSheet(log_title_style())
        toolbar.addWidget(title)

        toolbar.addStretch()

        filter_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "filter.svg"), "Filter", tone="log"
        )
        filter_btn.setCheckable(True)
        toolbar.addWidget(filter_btn)

        copy_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "copy.svg"), "Copy", tone="log"
        )
        toolbar.addWidget(copy_btn)

        export_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "export.svg"), "Export", tone="log"
        )
        toolbar.addWidget(export_btn)

        clear_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), "Clear", tone="log"
        )
        toolbar.addWidget(clear_btn)

        scroll_btn = self._make_sc_btn(
            os.path.join(_SVG_LOGS_DIR, "auto-scroll.svg"), "Auto-scroll", tone="log"
        )
        scroll_btn.setCheckable(True)
        scroll_btn.setChecked(True)
        scroll_btn.setStyleSheet(log_toolbar_button_style(checked_variant=True))
        toolbar.addWidget(scroll_btn)

        layout.addLayout(toolbar)

        filter_row = QWidget()
        filter_row.setVisible(False)
        filter_row.setStyleSheet(transparent_background_style())
        filter_layout = QHBoxLayout(filter_row)
        filter_layout.setContentsMargins(6, 0, 6, 4)
        filter_layout.setSpacing(6)
        filter_input = QLineEdit()
        filter_input.setPlaceholderText("Enter keyword or regex...")
        filter_input.setStyleSheet(filter_input_style())
        filter_layout.addWidget(filter_input, 1)
        filter_match_label = QLabel("")
        filter_match_label.setStyleSheet(filter_match_label_style())
        filter_layout.addWidget(filter_match_label)
        layout.addWidget(filter_row)

        log_edit = QTextEdit()
        log_edit.setReadOnly(True)
        log_edit.setContextMenuPolicy(Qt.CustomContextMenu)
        log_edit.setStyleSheet(log_edit_style(padding="6px 8px") + SERIAL_SCROLLBAR_STYLE)
        log_edit.document().setDefaultStyleSheet(log_document_style())
        log_edit.document().setMaximumBlockCount(5000)
        layout.addWidget(log_edit, 1)

        status_bar = QFrame()
        status_bar.setObjectName("scStatusBar")
        status_bar.setFixedHeight(30)
        status_bar.setStyleSheet(status_bar_style())
        sb_layout = QHBoxLayout(status_bar)
        sb_layout.setContentsMargins(12, 2, 12, 2)
        sb_layout.setSpacing(16)

        port_label = QLabel(f"Port: {config.get('port', 'Unconnected')}")
        port_label.setStyleSheet(status_label_style("error", compact=True))
        sb_layout.addWidget(port_label)

        baud_label = QLabel(f"Baud rate: {config.get('baudrate', '-')}")
        baud_label.setStyleSheet(status_label_style("muted"))
        sb_layout.addWidget(baud_label)

        rx_label = QLabel("RX: 0 B")
        rx_label.setStyleSheet(status_label_style("rx", compact=True))
        sb_layout.addWidget(rx_label)

        tx_label = QLabel("TX: 0 B")
        tx_label.setStyleSheet(status_label_style("tx", compact=True))
        sb_layout.addWidget(tx_label)

        sb_layout.addStretch()
        layout.addWidget(status_bar)

        panel = {
            "frame": frame,
            "log_edit": log_edit,
            "clear_btn": clear_btn,
            "scroll_btn": scroll_btn,
            "filter_btn": filter_btn,
            "filter_row": filter_row,
            "filter_input": filter_input,
            "filter_match_label": filter_match_label,
            "copy_btn": copy_btn,
            "export_btn": export_btn,
            "port_label": port_label,
            "baud_label": baud_label,
            "rx_label": rx_label,
            "tx_label": tx_label,
            "title_label": title,
            "config": config,
            "conn": None,
            "read_thread": None,
            "read_worker": None,
            "rx_bytes": 0,
            "tx_bytes": 0,
            "auto_scroll": True,
            "all_logs": [],
            "pending_html": [],
            "session_id": None,
        }

        clear_btn.clicked.connect(lambda _=None, p=panel: self._sc_extra_panel_clear(p))
        scroll_btn.clicked.connect(lambda checked, p=panel: self._sc_extra_panel_toggle_scroll(p, checked))
        filter_btn.clicked.connect(lambda checked, p=panel: self._sc_extra_panel_toggle_filter(p, checked))
        copy_btn.clicked.connect(lambda _=None, p=panel: self._sc_extra_panel_copy(p))
        export_btn.clicked.connect(lambda _=None, p=panel: self._sc_extra_panel_export(p))
        filter_input.returnPressed.connect(lambda p=panel: self._sc_extra_panel_apply_filter(p))

        frame.customContextMenuRequested.connect(
            lambda pos, p=panel: self._sc_extra_panel_context_menu(p, frame.mapToGlobal(pos))
        )
        log_edit.customContextMenuRequested.connect(
            lambda pos, p=panel: self._sc_extra_panel_context_menu(p, log_edit.mapToGlobal(pos))
        )
        frame.mousePressEvent = lambda event, p=panel: self._sc_on_log_panel_clicked(p, event)
        log_edit.mouseReleaseEvent = lambda event, p=panel, orig=log_edit.mouseReleaseEvent: (
            self._sc_on_log_panel_clicked(p, event), orig(event)
        )

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

    def _sc_extra_panel_toggle_scroll(self, panel, checked):
        panel["auto_scroll"] = checked
        if checked:
            sb = panel["log_edit"].verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

    def _sc_extra_panel_toggle_filter(self, panel, checked):
        panel["filter_row"].setVisible(checked)
        if not checked:
            panel["filter_input"].clear()
            panel["filter_match_label"].setText("")
            self._sc_extra_panel_show_all_logs(panel)
        else:
            panel["filter_input"].setFocus()

    def _sc_extra_panel_copy(self, panel):
        from PySide6.QtWidgets import QApplication
        text = panel["log_edit"].toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self._sc_extra_panel_append_log(panel, "[INFO] Log copied to clipboard", _CLR_TEXT_INFO)

    def _sc_extra_panel_export(self, panel):
        from PySide6.QtWidgets import QFileDialog
        title_text = panel.get("title_label")
        default_name = title_text.text() if title_text else "serial_log"
        default_name = default_name.replace(" ", "_").lower()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Log", f"{default_name}.log", "Log Files (*.log);;Text Files (*.txt);;All (*.*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(panel["log_edit"].toPlainText())
            self._sc_extra_panel_append_log(panel, f"[INFO] Log exported: {file_path}", _CLR_TEXT_INFO)
        except Exception as e:
            self._sc_extra_panel_append_log(panel, f"[ERROR] Export failed: {e}", extra_log_error_color())

    def _sc_extra_panel_apply_filter(self, panel):
        keyword = panel["filter_input"].text().strip()
        if not keyword:
            self._sc_extra_panel_show_all_logs(panel)
            panel["filter_match_label"].setText("")
            return
        log_edit = panel["log_edit"]
        log_edit.clear()
        count = 0
        for msg, html in panel["all_logs"]:
            if keyword.lower() in msg.lower():
                log_edit.append(html)
                count += 1
        panel["filter_match_label"].setText(f"{count} match{'es' if count != 1 else ''}")
        if panel["auto_scroll"]:
            sb = log_edit.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

    def _sc_extra_panel_show_all_logs(self, panel):
        log_edit = panel["log_edit"]
        log_edit.clear()
        for _, html in panel["all_logs"]:
            log_edit.append(html)
        if panel["auto_scroll"]:
            sb = log_edit.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

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

    def _sc_on_primary_panel_clicked(self, event):
        if self._sc_active_log_panel_index != 0:
            self._sc_active_log_panel_index = 0
            self._sc_active_session_id = "primary"
            self._sc_session_manager.set_active_session("primary")
            self._sc_update_panel_focus_style()

    def _sc_on_log_panel_clicked(self, panel, event):
        try:
            idx = self._sc_extra_log_panels.index(panel) + 1
        except ValueError:
            return
        if self._sc_active_log_panel_index != idx:
            self._sc_active_log_panel_index = idx
            session_id = panel.get("session_id")
            if session_id:
                self._sc_active_session_id = session_id
                self._sc_session_manager.set_active_session(session_id)
            self._sc_update_panel_focus_style()

    def _sc_update_panel_focus_style(self):
        active_border = f"2px solid {_CLR_CONNECT_FG}"
        inactive_border = f"2px solid {_CLR_BG_LOG}"

        if self._sc_active_log_panel_index == 0:
            self._sc_log_area.setStyleSheet(
                f"QFrame#scLogFrame {{ background-color: {_CLR_BG_LOG}; border: {active_border}; border-radius: 6px; }}"
            )
        else:
            self._sc_log_area.setStyleSheet(
                f"QFrame#scLogFrame {{ background-color: {_CLR_BG_LOG}; border: {inactive_border}; border-radius: 6px; }}"
            )

        for i, p in enumerate(self._sc_extra_log_panels):
            if self._sc_active_log_panel_index == i + 1:
                p["frame"].setStyleSheet(
                    f"QFrame#scLogFrame {{ background-color: {_CLR_BG_LOG}; border: {active_border}; border-radius: 6px; }}"
                )
            else:
                p["frame"].setStyleSheet(
                    f"QFrame#scLogFrame {{ background-color: {_CLR_BG_LOG}; border: {inactive_border}; border-radius: 6px; }}"
                )

    def _sc_extra_panel_context_menu(self, panel, global_pos):
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {_CLR_BG_CARD}; border: 1px solid {_CLR_BORDER_HOVER};
                border-radius: 6px; padding: 4px 0px;
            }}
            QMenu::item {{
                padding: 6px 20px; color: {_CLR_INPUT_TEXT}; font-size: 12px; font-family: {_UI_FONT};
            }}
            QMenu::item:selected {{
                background-color: {_CLR_BORDER}; color: #ffffff;
            }}
            QMenu::separator {{
                height: 1px; background: {_CLR_BORDER}; margin: 4px 8px;
            }}
        """)

        is_connected = False
        if DEBUG_MOCK:
            session_id = panel.get("session_id")
            if session_id:
                session = self._sc_session_manager.get_session(session_id)
                is_connected = session is not None and session.connected
            else:
                is_connected = panel.get("port_label") and "MOCK" in panel["port_label"].text()
        else:
            is_connected = panel.get("conn") is not None and panel["conn"].is_open

        if is_connected:
            disconnect_act = QAction("Disconnect", self)
            disconnect_act.triggered.connect(lambda: self._sc_extra_panel_do_disconnect(panel))
            menu.addAction(disconnect_act)
        else:
            connect_act = QAction("Connect", self)
            connect_act.triggered.connect(lambda: self._sc_extra_panel_connect(panel))
            menu.addAction(connect_act)

        menu.addSeparator()

        settings_act = QAction("Settings...", self)
        settings_act.triggered.connect(lambda: self._sc_extra_panel_settings(panel))
        menu.addAction(settings_act)

        menu.addSeparator()

        remove_act = QAction("Remove Panel", self)
        remove_act.triggered.connect(lambda: self._sc_remove_specific_panel(panel))
        menu.addAction(remove_act)

        menu.exec(global_pos)

    def _sc_extra_panel_do_disconnect(self, panel):
        self._sc_extra_panel_disconnect(panel)
        panel["port_label"].setText("Port: Disconnected")
        panel["port_label"].setStyleSheet(status_label_style("error", compact=True))
        self._sc_extra_panel_append_log(panel, "[INFO] Disconnected", _CLR_TEXT_INFO)

    def _sc_extra_panel_settings(self, panel):
        dlg = _PanelSettingsDialog(panel["config"], parent=self)
        if dlg.exec() != QDialog.Accepted:
            return
        new_config = dlg.get_config()

        if DEBUG_MOCK:
            session_id = panel.get("session_id")
            session = self._sc_session_manager.get_session(session_id) if session_id else None
            was_connected = session is not None and session.connected
        else:
            was_connected = panel.get("conn") is not None and panel["conn"].is_open
        if was_connected:
            self._sc_extra_panel_do_disconnect(panel)

        panel["config"] = new_config
        panel["title_label"].setText(new_config.get("title", "Serial Log"))
        panel["baud_label"].setText(f"Baud rate: {new_config.get('baudrate', '-')}")
        panel["port_label"].setText(f"Port: {new_config.get('port', 'Unconnected')}")
        panel["port_label"].setStyleSheet(status_label_style("error", compact=True))

        self._sc_extra_panel_append_log(
            panel,
            f"[INFO] Settings updated: {new_config.get('port', 'N/A')} @ {new_config.get('baudrate', 'N/A')}",
            _CLR_TEXT_INFO,
        )

        if new_config.get("auto_connect", False):
            self._sc_extra_panel_connect(panel)

    def _sc_remove_specific_panel(self, panel):
        if panel not in self._sc_extra_log_panels:
            return
        idx = self._sc_extra_log_panels.index(panel)
        self._sc_extra_log_panels.remove(panel)
        self._sc_extra_panel_disconnect(panel)
        panel["frame"].setParent(None)
        panel["frame"].deleteLater()
        self._sc_relayout_log_panels()
        self._sc_remove_log_btn.setEnabled(len(self._sc_extra_log_panels) > 0)
        if self._sc_active_log_panel_index == idx + 1:
            self._sc_active_log_panel_index = 0
            self._sc_active_session_id = "primary"
            self._sc_session_manager.set_active_session("primary")
            self._sc_update_panel_focus_style()
        elif self._sc_active_log_panel_index > idx + 1:
            self._sc_active_log_panel_index -= 1
        self._sc_append_system("[INFO] LOG panel removed", force_primary=True)

    def _sc_extra_panel_connect(self, panel):
        config = panel["config"]
        port = config.get("port", "")
        baudrate = config.get("baudrate", 115200)

        if not port:
            return

        panel_idx = self._sc_extra_log_panels.index(panel) if panel in self._sc_extra_log_panels else 0
        session_id = f"extra_{panel_idx}_{port}"
        panel["session_id"] = session_id

        session = self._sc_session_manager.get_session(session_id)
        if session is None:
            session = self._sc_session_manager.create_session(
                session_id=session_id,
                display_name=config.get("title", f"LOG-{panel_idx + 2}"),
                auto_activate=False,
            )
        session.configure(
            port=port, baudrate=baudrate,
            bytesize=config.get("databit", 8),
            stopbits={"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}.get(
                config.get("stopbit", "1"), serial.STOPBITS_ONE
            ),
            parity={"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD,
                    "Mark": serial.PARITY_MARK, "Space": serial.PARITY_SPACE}.get(
                config.get("parity", "None"), serial.PARITY_NONE
            ),
            xonxoff=(config.get("flow", "None") == "XON/XOFF"),
            rtscts=(config.get("flow", "None") == "RTS/CTS"),
        )

        if DEBUG_MOCK:
            panel["conn"] = None
            session._connected = True
            panel["port_label"].setText("Port: MOCK")
            panel["port_label"].setStyleSheet(status_label_style("connected", include_font=True))
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
            session._serial_conn = conn
            session._connected = True
            panel["port_label"].setText(f"Port: {port}")
            panel["port_label"].setStyleSheet(status_label_style("connected", include_font=True))
            self._sc_extra_panel_append_log(panel, f"[INFO] Connected: {port} @ {baudrate}", _CLR_TEXT_INFO)
            self._sc_extra_panel_start_read(panel)
        except Exception as e:
            self._sc_extra_panel_append_log(panel, f"[ERROR] Connection failed: {e}", extra_log_error_color())

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
        session_id = panel.get("session_id")
        if session_id:
            self._sc_session_manager.remove_session(session_id)
            panel["session_id"] = None

    def _sc_extra_panel_start_read(self, panel):
        if panel["conn"] is None or not panel["conn"].is_open:
            return
        worker = _SerialReadWorker(panel["conn"])
        thread = QThread(self)
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
        dlg.rx_use_ntp_cb.setChecked(self._sc_use_ntp)
        dlg.rx_max_lines_spin.setValue(getattr(self, '_sc_max_log_lines', 10000))

        dlg.tx_hex_toggle.set_value("HEX" if self._sc_tx_display_hex else "ASCII")
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
            self._sc_apply_ntp_setting(dlg.rx_use_ntp_cb.isChecked())
            self._sc_max_log_lines = dlg.rx_max_lines_spin.value()

            tx_val = dlg.tx_hex_toggle.value()
            self._sc_tx_display_hex = tx_val == "HEX"
            self._sc_tx_toggle.set_value(tx_val)

            ending_idx = dlg.ending_combo.currentIndex()
            self._sc_ending_combo.setCurrentIndex(ending_idx)

            self._sc_show_send_cb.setChecked(dlg.show_send_cb.isChecked())
            self._sc_line_by_line_cb.setChecked(dlg.line_by_line_cb.isChecked())

            self._sc_log_auto_save = dlg.log_auto_save_cb.isChecked()
            self._sc_log_save_path = dlg.log_save_path_edit.text()
            if self._sc_log_auto_save and self._serial_connected:
                if self._sc_log_file_handle is None:
                    self._sc_start_auto_save()
            elif not self._sc_log_auto_save:
                self._sc_stop_auto_save()

            font_family = dlg.display_font_combo.currentText()
            font_size = dlg.display_font_size_spin.value()
            self._sc_display_font = font_family
            self._sc_display_font_size = font_size
            self._sc_log_edit.setStyleSheet(
                log_edit_style(
                    font_family=font_family,
                    font_size=font_size,
                    padding="4px 6px",
                    include_line_height=True,
                ) + SERIAL_SCROLLBAR_STYLE
            )

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
        if not path:
            return
        temp_file = self._sc_log_temp_path
        if temp_file and os.path.isfile(temp_file):
            if self._sc_log_temp_handle is not None:
                try:
                    self._sc_log_temp_handle.flush()
                except OSError:
                    pass
            try:
                import shutil
                shutil.copy2(temp_file, path)
                return
            except OSError:
                pass
        with open(path, "w", encoding="utf-8") as f:
            for raw, _ in self._sc_all_logs:
                f.write(raw + "\n")

    @staticmethod
    def _sc_strip_timestamp(raw: str) -> str:
        return re.sub(r'^\d{2}:\d{2}:\d{2}\.\d{3}\s', '', raw)

    def _sc_on_save_toggle(self, checked: bool):
        if checked:
            if not self._sc_start_manual_save():
                self._sc_save_btn.setChecked(False)
        else:
            self._sc_stop_manual_save()

    def _sc_start_manual_save(self) -> bool:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_dir = getattr(self, '_sc_log_save_path', '') or self._sc_fallback_dir()
        default_name = f"serial_log_{ts}.txt"
        dlg = _SerialSaveDialog(
            self,
            default_dir=default_dir,
            default_name=default_name,
            keep_timestamp=self._sc_save_keep_timestamp,
        )
        if dlg.exec() != QDialog.Accepted:
            return False
        cfg = dlg.get_config()
        save_dir = cfg["directory"]
        name = cfg["name"]
        keep_ts = cfg["keep_timestamp"]
        if not name:
            name = default_name
        if not name.lower().endswith(".txt"):
            name += ".txt"
        if not save_dir:
            save_dir = self._sc_fallback_dir()
        try:
            os.makedirs(save_dir, exist_ok=True)
        except OSError as exc:
            logger.error("Save: cannot create directory %s", save_dir, exc_info=True)
            QMessageBox.warning(self, "Save", f"Cannot create directory:\n{exc}")
            return False
        file_path = os.path.join(save_dir, name)
        if os.path.exists(file_path):
            reply = QMessageBox.question(
                self, "Save",
                f"File already exists:\n{file_path}\n\nOverwrite it?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return False
        try:
            handle = open(file_path, "w", encoding="utf-8")
        except OSError as exc:
            logger.error("Save: cannot open file %s", file_path, exc_info=True)
            QMessageBox.warning(self, "Save", f"Cannot open file:\n{exc}")
            return False

        self._sc_save_keep_timestamp = keep_ts
        try:
            self._sc_write_buffer_to_handle(handle, keep_ts)
            handle.flush()
        except OSError:
            logger.error("Save: failed writing buffer to %s", file_path, exc_info=True)
            try:
                handle.close()
            except OSError:
                pass
            QMessageBox.warning(self, "Save", "Failed to write existing buffer.")
            return False

        self._sc_save_handle = handle
        self._sc_save_path = file_path
        self._sc_log_save_path = save_dir
        self._sc_append_system(f"[INFO] Save started: {file_path}", force_primary=True)
        return True

    def _sc_write_buffer_to_handle(self, handle, keep_ts: bool):
        written = False
        temp_file = self._sc_log_temp_path
        if temp_file and os.path.isfile(temp_file):
            if self._sc_log_temp_handle is not None:
                try:
                    self._sc_log_temp_handle.flush()
                except OSError:
                    pass
            try:
                with open(temp_file, "r", encoding="utf-8") as src:
                    for line in src:
                        line = line.rstrip("\n")
                        out = line if keep_ts else self._sc_strip_timestamp(line)
                        handle.write(out + "\n")
                written = True
            except OSError:
                written = False
        if not written:
            for raw, _ in self._sc_all_logs:
                out = raw if keep_ts else self._sc_strip_timestamp(raw)
                handle.write(out + "\n")

    def _sc_stop_manual_save(self):
        if self._sc_save_handle is not None:
            path = self._sc_save_path
            try:
                self._sc_save_handle.flush()
                self._sc_save_handle.close()
            except OSError:
                pass
            self._sc_save_handle = None
            if path:
                self._sc_append_system(f"[INFO] Save stopped: {path}", force_primary=True)
            self._sc_save_path = None

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
        self._sc_start_temp_log()
        if self._sc_log_file_handle is not None and self._serial_connected:
            self._sc_stop_auto_save()
            self._sc_start_auto_save()

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

            ok = self._sc_send_to_focused_panel(data)
            if ok:
                if self._sc_active_log_panel_index == 0:
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

    def _sc_send_to_focused_panel(self, data) -> bool:
        if self._sc_active_log_panel_index == 0:
            return self.serial_send(data)

        panel_idx = self._sc_active_log_panel_index - 1
        if panel_idx < 0 or panel_idx >= len(self._sc_extra_log_panels):
            return self.serial_send(data)

        panel = self._sc_extra_log_panels[panel_idx]
        conn = panel.get("conn")

        if DEBUG_MOCK:
            panel["tx_bytes"] = panel.get("tx_bytes", 0) + len(data)
            panel["tx_label"].setText(self._sc_format_bytes("TX", panel["tx_bytes"]))
            self._sc_extra_panel_append_log(
                panel, f"[TX] {data.decode('utf-8', errors='replace')}", _CLR_TX
            )
            return True

        if conn is None or not conn.is_open:
            return False
        try:
            conn.write(data)
            panel["tx_bytes"] = panel.get("tx_bytes", 0) + len(data)
            panel["tx_label"].setText(self._sc_format_bytes("TX", panel["tx_bytes"]))
            self._sc_extra_panel_append_log(
                panel, f"[TX] {data.decode('utf-8', errors='replace')}", _CLR_TX
            )
            return True
        except Exception as e:
            self._sc_extra_panel_append_log(panel, f"[ERROR] Send failed: {e}", extra_log_error_color())
            return False

    def _sc_on_data_received(self, data: bytes):
        if self._sc_paused:
            return
        if self._sc_script_wait_keyword:
            try:
                self._sc_script_feed_rx(data.decode("utf-8", errors="replace"))
            except Exception:
                pass
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
                        f"[INFO] Current baudrate {self._serial_baudrate} score={s}, locked.",
                        force_primary=True,
                    )
                    monitor.state = AutoBaudState.LOCKED
                    monitor.reset()
                    self._sc_on_auto_baud_state_changed(AutoBaudState.LOCKED.value)
                else:
                    score_info = f"score={s}" if s is not None else "no data"
                    self._sc_append_system(
                        f"[INFO] Current baudrate {self._serial_baudrate} {score_info}, scanning candidates...",
                        force_primary=True,
                    )
                    self._sc_start_auto_baud_scan("initial")
            return
        monitor.hex_mode = self._sc_rx_display_hex
        result = monitor.on_rx_data(data)
        if result is None:
            return
        action = result.get("action")
        if action == "suspect":
            self._sc_append_system("[INFO] RX quality degraded. Enter SUSPECT state.", force_primary=True)
            self._sc_on_auto_baud_state_changed(AutoBaudState.SUSPECT.value)
        elif action == "recovered":
            self._sc_append_system("[INFO] RX quality recovered.", force_primary=True)
            self._sc_on_auto_baud_state_changed(AutoBaudState.LOCKED.value)
        elif action == "scan_needed":
            self._sc_append_system("[INFO] Sustained RX quality issue. Starting rescan...", force_primary=True)
            self._sc_start_auto_baud_scan("runtime")

    # --- quick commands (项目 -> 分组 -> 指令) ---

    # ==================== Scripts 子系统 ====================

    @staticmethod
    def _sc_script_default_data():
        return {
            "version": "1.0",
            "last_script_id": "",
            "scripts": [],
        }

    @staticmethod
    def _sc_script_default_step():
        return {
            "cmd": "",
            "priority": 1,
            "wait_ms": 1000,
            "send_type": "text",
            "line_ending": "\r\n",
            "wait_keyword": "",
            "wait_timeout_ms": 0,
        }

    def _sc_script_table_qss(self) -> str:
        return (
            f"QTableWidget {{"
            f"  background: transparent;"
            f"  color: {_CLR_TEXT_BODY};"
            f"  border: none;"
            f"  gridline-color: transparent;"
            f"  font-size: 12px;"
            f"  outline: none;"
            f"}}"
            f"QTableWidget::item {{ padding: 4px 6px; border: none; }}"
            f"QHeaderView::section {{"
            f"  background: transparent;"
            f"  color: {_CLR_TEXT_MUTED};"
            f"  border: none;"
            f"  border-bottom: 1px solid {_CLR_BORDER};"
            f"  padding: 5px 6px;"
            f"  font-size: 11px;"
            f"  font-weight: 600;"
            f"}}"
            f"QTableCornerButton::section {{"
            f"  background: transparent;"
            f"  border: none;"
            f"}}"
        )

    def _sc_script_current(self):
        sid = self._sc_script_data.get("last_script_id", "")
        for s in self._sc_script_data.get("scripts", []):
            if s.get("id") == sid:
                return s
        scripts = self._sc_script_data.get("scripts", [])
        return scripts[0] if scripts else None

    def _sc_script_refresh_all(self):
        if not hasattr(self, "_sc_script_combo"):
            return
        combo = self._sc_script_combo
        combo.blockSignals(True)
        combo.clear()
        scripts = self._sc_script_data.get("scripts", [])
        for s in scripts:
            combo.addItem(s.get("name", "未命名"), s.get("id", ""))
        cur = self._sc_script_current()
        if cur is not None:
            idx = combo.findData(cur.get("id", ""))
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            self._sc_script_data["last_script_id"] = cur.get("id", "")
        combo.blockSignals(False)
        self._sc_script_sync_loop_widgets()
        self._sc_script_refresh_table()

    def _sc_script_sync_loop_widgets(self):
        cur = self._sc_script_current()
        if cur is None:
            return
        self._sc_script_loop_cb.blockSignals(True)
        self._sc_script_loop_spin.blockSignals(True)
        self._sc_script_loop_cb.setChecked(bool(cur.get("loop", False)))
        self._sc_script_loop_spin.setValue(int(cur.get("loop_count", 1)) or 1)
        self._sc_script_loop_cb.blockSignals(False)
        self._sc_script_loop_spin.blockSignals(False)

    def _sc_script_refresh_table(self, running_index: int = -1):
        table = self._sc_script_table
        cur = self._sc_script_current()
        steps = self._sc_script_ordered_steps(cur) if cur else []
        table.setRowCount(len(steps))
        for row, step in enumerate(steps):
            cmd = step.get("cmd", "")
            if step.get("wait_keyword"):
                cmd = f"{cmd}  ⟶ wait \"{step['wait_keyword']}\""
            prio = str(step.get("priority", 1))
            wait = str(step.get("wait_ms", 0))
            if running_index < 0:
                status = "Pending"
            elif row < running_index:
                status = "✓ Done"
            elif row == running_index:
                status = "▶ Running"
            else:
                status = "Pending"
            for col, text in enumerate((str(row + 1), cmd, prio, wait, status)):
                item = QTableWidgetItem(text)
                if col in (0, 2, 3):
                    item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, col, item)

    @staticmethod
    def _sc_script_ordered_steps(script) -> list:
        if not script:
            return []
        steps = [s for s in script.get("steps", []) if int(s.get("priority", 0)) > 0]
        return sorted(steps, key=lambda s: int(s.get("priority", 0)))

    def _sc_script_on_combo_changed(self, _index: int):
        sid = self._sc_script_combo.currentData()
        if sid:
            self._sc_script_data["last_script_id"] = sid
            self._sc_script_sync_loop_widgets()
            self._sc_script_refresh_table()

    def _sc_script_on_loop_toggled(self, checked: bool):
        cur = self._sc_script_current()
        if cur is not None:
            cur["loop"] = bool(checked)
            self._sc_save_persisted_state()

    def _sc_script_on_loop_count_changed(self, value: int):
        cur = self._sc_script_current()
        if cur is not None:
            cur["loop_count"] = int(value)
            self._sc_save_persisted_state()

    # ---- 编辑 / 增删 ----

    def _sc_script_new(self):
        script = {
            "id": self._sc_qc_gen_id("script"),
            "name": "新脚本",
            "loop": False,
            "loop_count": 1,
            "steps": [self._sc_script_default_step()],
        }
        dlg = _SerialScriptEditorDialog(self, script)
        if dlg.exec() == QDialog.Accepted:
            self._sc_script_data.setdefault("scripts", []).append(dlg.get_script())
            self._sc_script_data["last_script_id"] = script["id"]
            self._sc_save_persisted_state()
            self._sc_script_refresh_all()

    def _sc_script_edit(self):
        cur = self._sc_script_current()
        if cur is None:
            QMessageBox.information(self, "提示", "请先新建一个脚本")
            return
        dlg = _SerialScriptEditorDialog(self, cur)
        if dlg.exec() == QDialog.Accepted:
            edited = dlg.get_script()
            cur.update(edited)
            self._sc_save_persisted_state()
            self._sc_script_refresh_all()

    def _sc_script_delete(self):
        cur = self._sc_script_current()
        if cur is None:
            return
        if QMessageBox.question(
            self, "删除脚本", f"确定删除脚本 “{cur.get('name', '')}” ?"
        ) != QMessageBox.Yes:
            return
        scripts = self._sc_script_data.get("scripts", [])
        scripts.remove(cur)
        self._sc_script_data["last_script_id"] = scripts[0]["id"] if scripts else ""
        self._sc_save_persisted_state()
        self._sc_script_refresh_all()

    # ---- txt 导入 / 导出 ----

    def _sc_script_import_txt(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入脚本 (.txt)", "", "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))
            return
        steps = []
        priority = 1
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            step = self._sc_script_default_step()
            step["cmd"] = parts[0]
            if len(parts) >= 2 and parts[1]:
                try:
                    step["priority"] = int(parts[1])
                except ValueError:
                    step["priority"] = priority
            else:
                step["priority"] = priority
            if len(parts) >= 3 and parts[2]:
                try:
                    step["wait_ms"] = int(parts[2])
                except ValueError:
                    pass
            steps.append(step)
            priority += 1
        if not steps:
            QMessageBox.warning(self, "导入失败", "未解析到有效指令行")
            return
        name = os.path.splitext(os.path.basename(path))[0]
        script = {
            "id": self._sc_qc_gen_id("script"),
            "name": name,
            "loop": False,
            "loop_count": 1,
            "steps": steps,
        }
        self._sc_script_data.setdefault("scripts", []).append(script)
        self._sc_script_data["last_script_id"] = script["id"]
        self._sc_save_persisted_state()
        self._sc_script_refresh_all()
        self._sc_append_system(f"[SCRIPT] 已导入脚本 “{name}” ({len(steps)} 步)")

    def _sc_script_export_txt(self):
        cur = self._sc_script_current()
        if cur is None:
            QMessageBox.information(self, "提示", "没有可导出的脚本")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "导出脚本 (.txt)", f"{cur.get('name', 'script')}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        if not path:
            return
        lines = [
            "# 格式: 指令,优先级,等待ms  (优先级=0 表示跳过)",
            f"# 脚本: {cur.get('name', '')}",
        ]
        for step in cur.get("steps", []):
            lines.append(
                f"{step.get('cmd', '')},{step.get('priority', 1)},{step.get('wait_ms', 0)}"
            )
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as e:
            QMessageBox.critical(self, "导出失败", str(e))
            return
        self._sc_append_system(f"[SCRIPT] 已导出脚本到 {path}")

    # ---- 运行引擎 ----

    def _sc_script_run(self):
        if self._sc_script_running:
            return
        cur = self._sc_script_current()
        if cur is None:
            QMessageBox.information(self, "提示", "请先新建或选择一个脚本")
            return
        steps = self._sc_script_ordered_steps(cur)
        if not steps:
            QMessageBox.warning(self, "提示", "脚本没有可执行的步骤 (优先级需 > 0)")
            return

        self._sc_script_steps = steps
        self._sc_script_step_index = 0
        loop_on = self._sc_script_loop_cb.isChecked()
        self._sc_script_loop_remaining = (
            int(self._sc_script_loop_spin.value()) if loop_on else 1
        )
        self._sc_script_running = True
        self._sc_script_set_controls_enabled(False)
        self._sc_append_system(
            f"[SCRIPT] 开始执行 “{cur.get('name', '')}” "
            f"({len(steps)} 步, 循环 x{self._sc_script_loop_remaining})"
        )
        self._sc_script_refresh_table(running_index=0)
        self._sc_script_exec_current_step()

    def _sc_script_set_controls_enabled(self, enabled: bool):
        self._sc_script_run_btn.setEnabled(enabled)
        self._sc_script_stop_btn.setEnabled(not enabled)
        self._sc_script_combo.setEnabled(enabled)
        self._sc_script_new_btn.setEnabled(enabled)
        self._sc_script_edit_btn.setEnabled(enabled)
        self._sc_script_del_btn.setEnabled(enabled)
        self._sc_script_import_btn.setEnabled(enabled)
        self._sc_script_export_btn.setEnabled(enabled)
        self._sc_script_loop_cb.setEnabled(enabled)
        self._sc_script_loop_spin.setEnabled(enabled)

    def _sc_script_exec_current_step(self):
        if not self._sc_script_running:
            return
        idx = self._sc_script_step_index
        steps = self._sc_script_steps
        if idx >= len(steps):
            self._sc_script_on_loop_end()
            return

        step = steps[idx]
        self._sc_script_refresh_table(running_index=idx)
        self._sc_script_status_label.setText(
            f"\u2022 Running (Step {idx + 1}/{len(steps)})"
        )
        self._sc_script_status_label.setStyleSheet(status_label_style("ok", include_font=True))

        cmd = step.get("cmd", "")
        ok = self._sc_script_send_step(step)
        if not ok:
            self._sc_append_system("[SCRIPT] 发送失败，串口未连接，已停止")
            self._sc_script_stop()
            return

        keyword = step.get("wait_keyword", "").strip()
        wait_ms = max(0, int(step.get("wait_ms", 0)))
        if keyword:
            self._sc_script_wait_keyword = keyword
            self._sc_script_wait_buffer = ""
            timeout = int(step.get("wait_timeout_ms", 0)) or wait_ms or 5000
            self._sc_script_timer.start(timeout)
        else:
            self._sc_script_wait_keyword = ""
            self._sc_script_timer.start(wait_ms)

    def _sc_script_send_step(self, step) -> bool:
        cmd = step.get("cmd", "")
        send_type = step.get("send_type", "text")
        if send_type == "hex":
            try:
                data = bytes.fromhex(cmd.replace(" ", ""))
            except ValueError:
                self._sc_append_system(f"[SCRIPT][ERROR] Invalid HEX: {cmd}")
                return False
        else:
            data = (cmd + step.get("line_ending", "\r\n")).encode("utf-8")

        ok = self._sc_send_to_focused_panel(data)
        if ok and self._sc_active_log_panel_index == 0:
            self._sc_tx_bytes += len(data)
            self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))
            if self._sc_show_send:
                display = cmd if send_type != "hex" else data.hex(' ')
                self._sc_append_log(f"[TX] {display}", _CLR_TX)
        return ok

    def _sc_script_feed_rx(self, text: str):
        if not self._sc_script_wait_keyword:
            return
        self._sc_script_wait_buffer += text
        if len(self._sc_script_wait_buffer) > 4096:
            self._sc_script_wait_buffer = self._sc_script_wait_buffer[-4096:]
        if self._sc_script_wait_keyword in self._sc_script_wait_buffer:
            self._sc_script_wait_keyword = ""
            self._sc_script_wait_buffer = ""
            self._sc_script_timer.stop()
            QTimer.singleShot(0, self._sc_script_advance)

    def _sc_script_on_timeout(self):
        if not self._sc_script_running:
            return
        if self._sc_script_wait_keyword:
            self._sc_append_system(
                f"[SCRIPT] 等待关键字 “{self._sc_script_wait_keyword}” 超时，继续下一步"
            )
            self._sc_script_wait_keyword = ""
            self._sc_script_wait_buffer = ""
        self._sc_script_advance()

    def _sc_script_advance(self):
        if not self._sc_script_running:
            return
        self._sc_script_step_index += 1
        self._sc_script_exec_current_step()

    def _sc_script_on_loop_end(self):
        self._sc_script_loop_remaining -= 1
        if self._sc_script_loop_remaining > 0:
            self._sc_script_step_index = 0
            self._sc_append_system(
                f"[SCRIPT] 进入下一轮循环 (剩余 {self._sc_script_loop_remaining} 轮)"
            )
            self._sc_script_exec_current_step()
        else:
            self._sc_append_system("[SCRIPT] 执行完成")
            self._sc_script_finish()

    def _sc_script_stop(self):
        if not self._sc_script_running:
            return
        self._sc_append_system("[SCRIPT] 已手动停止")
        self._sc_script_finish()

    def _sc_script_finish(self):
        self._sc_script_running = False
        self._sc_script_wait_keyword = ""
        self._sc_script_wait_buffer = ""
        self._sc_script_timer.stop()
        self._sc_script_set_controls_enabled(True)
        self._sc_script_status_label.setText("\u2022 Idle")
        self._sc_script_status_label.setStyleSheet(status_label_style("muted", include_font=True))
        self._sc_script_refresh_table(running_index=-1)

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
            btn.set_preview_data(
                name=name,
                content=content,
                send_type=entry.get('send_type', 'text'),
                encoding=entry.get('encoding', 'ascii'),
                line_ending=entry.get('line_ending', ''),
            )
            btn.clicked.connect(
                lambda checked=False, e=entry: self._sc_send_quick(e)
            )
            # 右键菜单：编辑 / 删除
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, i=idx: self._sc_qc_on_cmd_btn_context_menu(b, pos, i)
            )
            btn.setStyleSheet(quick_command_button_style())
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
        target_session_id = entry.get("target_session_id", "")

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

        if target_session_id:
            ok = self.send_to_session(target_session_id, data)
        else:
            ok = self._sc_send_to_focused_panel(data)
        if ok:
            if self._sc_active_log_panel_index == 0 and not target_session_id:
                self._sc_tx_bytes += len(data)
                self._sc_status_tx_label.setText(self._sc_format_bytes("TX", self._sc_tx_bytes))
                if self._sc_show_send:
                    display = data.hex(' ') if send_type == "hex" else content
                    self._sc_append_log(f"[TX] {display}", _CLR_TX)
        else:
            target_info = f" (target: {target_session_id})" if target_session_id else ""
            self._sc_append_system(f"[ERROR] Send failed, serial not connected{target_info}")

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
            self._sc_append_system(f"[INFO] Exported project: {project.get('name', '')}", force_primary=True)
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
    _SC_APP_VERSION = "1.0.0"
    _SC_APP_AUTHOR = "KK_Lab Team"
    _SC_DEFAULT_WINDOW_SIZE = (1300, 850)
    _SC_WINDOW_MARGIN = 40

    def _sc_default_persisted_state(self, quick_commands=None, scripts=None) -> dict:
        return {
            "version": "2.0",
            "serial": {
                "port": "",
                "baudrate": "921600",
                "auto_detect": True,
                "databits": "8",
                "stopbits": "1",
                "parity": "None",
                "flow_control": "None",
                "auto_detect_config": dict(AUTO_BAUD_CONFIG),
            },
            "ui": {
                "rx_display_hex": False,
                "tx_display_hex": False,
                "show_timestamp": True,
                "use_ntp": False,
                "line_ending": "\r\n",
                "show_send": True,
                "line_by_line": False,
                "sidebar_visible": True,
                "center_split_sizes": [680, 155],
            },
            "send_history": [],
            "quick_commands": quick_commands or self._sc_qc_default_data(),
            "scripts": scripts or self._sc_script_default_data(),
        }

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

    def _sc_screen_available_geometry_for(self, point=None) -> QRect:
        app = QApplication.instance()
        screen = None
        if app is not None and point is not None:
            screen = app.screenAt(point)
        if screen is None and app is not None:
            screen = app.primaryScreen()
        if screen is not None:
            return screen.availableGeometry()
        return QRect(0, 0, 1280, 720)

    def _sc_default_window_geometry(self) -> QRect:
        available = self._sc_screen_available_geometry_for()
        target_w, target_h = self._SC_DEFAULT_WINDOW_SIZE
        margin = self._SC_WINDOW_MARGIN
        width = min(target_w, max(640, available.width() - margin), int(available.width() * 0.88))
        height = min(target_h, max(480, available.height() - margin), int(available.height() * 0.88))
        x = available.x() + max(0, (available.width() - width) // 2)
        y = available.y() + max(0, (available.height() - height) // 2)
        return QRect(x, y, width, height)

    def _sc_collect_window_state(self) -> dict:
        if not self.isWindow() or not self.isVisible() or self.isMinimized():
            return {}

        geom = self.normalGeometry() if self.isMaximized() else self.geometry()
        if geom.width() <= 0 or geom.height() <= 0:
            return {}

        return {
            "x": int(geom.x()),
            "y": int(geom.y()),
            "width": int(geom.width()),
            "height": int(geom.height()),
            "maximized": bool(self.isMaximized()),
        }

    def _sc_clamped_window_geometry(self, window_cfg: dict) -> QRect:
        saved = QRect(
            int(window_cfg.get("x", 0)),
            int(window_cfg.get("y", 0)),
            int(window_cfg.get("width", 0)),
            int(window_cfg.get("height", 0)),
        )
        if saved.width() <= 0 or saved.height() <= 0:
            return self._sc_default_window_geometry()

        available = self._sc_screen_available_geometry_for(saved.center())
        margin = self._SC_WINDOW_MARGIN
        max_w = max(1, available.width() - margin)
        max_h = max(1, available.height() - margin)
        width = min(saved.width(), max_w)
        height = min(saved.height(), max_h)

        x = min(max(saved.x(), available.x()), available.right() - width + 1)
        y = min(max(saved.y(), available.y()), available.bottom() - height + 1)
        return QRect(x, y, width, height)

    def _sc_apply_window_geometry(self) -> None:
        window_cfg = getattr(self, "_sc_window_geometry", None)
        if isinstance(window_cfg, dict):
            self.setGeometry(self._sc_clamped_window_geometry(window_cfg))
            self._sc_restore_maximized = bool(window_cfg.get("maximized", False))
            return

        self.setGeometry(self._sc_default_window_geometry())
        self._sc_restore_maximized = False

    def _sc_about_info(self) -> dict:
        mode = "Packaged" if getattr(_sys, "frozen", False) else "Development"
        app = QApplication.instance()
        screen_text = "Unknown"
        if app is not None and app.primaryScreen() is not None:
            geo = app.primaryScreen().availableGeometry()
            screen_text = f"{geo.width()} x {geo.height()} available"
        quick_count = 0
        qc_data = getattr(self, "_sc_qc_data", {})
        if isinstance(qc_data, dict):
            quick_count = sum(
                len(g.get("commands", []))
                for p in qc_data.get("projects", [])
                for g in p.get("groups", [])
            )
        return {
            "Application": "KK Serial Console",
            "Version": self._SC_APP_VERSION,
            "Author": self._SC_APP_AUTHOR,
            "Config schema": "2.0",
            "Config file": self._sc_persisted_path(),
            "Config directory": self._sc_user_config_dir(),
            "Quick Commands": str(quick_count),
            "Runtime mode": mode,
            "Primary screen": screen_text,
        }

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

        persisted = self._sc_default_persisted_state(
            quick_commands=getattr(self, "_sc_qc_data", self._sc_qc_default_data()),
            scripts=getattr(self, "_sc_script_data", self._sc_script_default_data()),
        )
        persisted["serial"].update({
            "port": port_text,
            "baudrate": baud_text,
            "auto_detect": auto_detect,
            "databits": databit,
            "stopbits": stopbit,
            "parity": parity,
            "flow_control": flow_ctrl,
            "auto_detect_config": auto_detect_config,
        })
        persisted["ui"].update({
            "rx_display_hex": getattr(self, "_sc_rx_display_hex", False),
            "tx_display_hex": getattr(self, "_sc_tx_display_hex", False),
            "show_timestamp": getattr(self, "_sc_show_timestamp", True),
            "use_ntp": getattr(self, "_sc_use_ntp", False),
            "line_ending": getattr(self, "_sc_line_ending", "\r\n"),
            "show_send": getattr(self, "_sc_show_send", True),
            "line_by_line": getattr(self, "_sc_line_by_line", False),
            "sidebar_visible": getattr(self, "_sc_sidebar_visible", True),
            "log_auto_save": getattr(self, "_sc_log_auto_save", False),
            "log_save_path": getattr(self, "_sc_log_save_path", ""),
            "center_split_sizes": (
                list(self._sc_center_splitter.sizes())
                if hasattr(self, "_sc_center_splitter")
                else []
            ),
        })
        persisted["send_history"] = list(getattr(self, "_sc_send_history", []))[-50:]
        window_state = self._sc_collect_window_state()
        if window_state:
            persisted["window"] = window_state
        elif isinstance(getattr(self, "_sc_window_geometry", None), dict):
            persisted["window"] = self._sc_window_geometry
        return persisted

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
                    ("use_ntp", "_sc_use_ntp"),
                    ("line_ending", "_sc_line_ending"),
                    ("show_send", "_sc_show_send"),
                    ("line_by_line", "_sc_line_by_line"),
                    ("sidebar_visible", "_sc_sidebar_visible"),
                    ("log_auto_save", "_sc_log_auto_save"),
                    ("log_save_path", "_sc_log_save_path"),
                ):
                    if key in ui_cfg:
                        setattr(self, attr, ui_cfg[key])
                if getattr(self, "_sc_use_ntp", False):
                    self._sc_apply_ntp_setting(True)

                split_sizes = ui_cfg.get("center_split_sizes")
                if (
                    isinstance(split_sizes, list)
                    and len(split_sizes) == 2
                    and all(isinstance(x, (int, float)) and x > 0 for x in split_sizes)
                    and hasattr(self, "_sc_center_splitter")
                ):
                    self._sc_center_splitter.setSizes([int(x) for x in split_sizes])

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

            scripts = data.get("scripts")
            if isinstance(scripts, dict) and isinstance(scripts.get("scripts"), list):
                self._sc_script_data = scripts
                if hasattr(self, "_sc_script_combo"):
                    self._sc_script_refresh_all()

            window_cfg = data.get("window")
            if isinstance(window_cfg, dict):
                self._sc_window_geometry = window_cfg
        else:
            for key, attr in (
                ("rx_display_hex", "_sc_rx_display_hex"),
                ("tx_display_hex", "_sc_tx_display_hex"),
                ("show_timestamp", "_sc_show_timestamp"),
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
                        self._sc_append_system(f"[WARN] Config corrupted, using defaults. Path: {source}", force_primary=True)
                elif not isinstance(raw, dict):
                    self._sc_qc_data = self._sc_qc_default_data()
                    if hasattr(self, "_sc_append_system"):
                        self._sc_append_system(f"[WARN] Config invalid format, using defaults. Path: {source}", force_primary=True)
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
                                f"[INFO] Loaded config from {origin}: {source} ({total} quick commands)",
                                force_primary=True,
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
                    self._sc_append_system(f"[INFO] Config path: {cfg_path}", force_primary=True)

            try:
                self._sc_qc_refresh_all()
            except Exception:
                pass
        except Exception:
            pass

    def _sc_save_persisted_state(self) -> None:
        if getattr(self, "_sc_skip_next_persist_save", False):
            self._sc_skip_next_persist_save = False
            return
        try:
            cfg_path = self._sc_persisted_path()
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(self._sc_collect_persisted_state(), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _sc_apply_reset_defaults_to_widgets(self) -> None:
        if hasattr(self, "_sc_port_combo"):
            self._sc_port_combo.setCurrentIndex(-1)
        if hasattr(self, "_sc_baud_combo"):
            self._sc_baud_combo.setCurrentText("921600")
        if hasattr(self, "_sc_auto_detect_cb"):
            self._sc_auto_detect_cb.setChecked(True)
        if hasattr(self, "_sc_databit_combo"):
            self._sc_databit_combo.setCurrentText("8")
        if hasattr(self, "_sc_stopbit_combo"):
            self._sc_stopbit_combo.setCurrentText("1")
        if hasattr(self, "_sc_parity_combo"):
            self._sc_parity_combo.setCurrentText("None")
        if hasattr(self, "_sc_flow_combo"):
            self._sc_flow_combo.setCurrentText("None")

        self._sc_rx_display_hex = False
        if hasattr(self, "_sc_rx_toggle"):
            self._sc_rx_toggle.set_value("ASCII")
        self._sc_tx_display_hex = False
        if hasattr(self, "_sc_tx_toggle"):
            self._sc_tx_toggle.set_value("ASCII")

        self._sc_show_timestamp = True
        if hasattr(self, "_sc_rx_show_time_cb"):
            self._sc_rx_show_time_cb.setChecked(True)
        self._sc_apply_ntp_setting(False)
        self._sc_line_ending = "\r\n"
        if hasattr(self, "_sc_ending_combo"):
            self._sc_ending_combo.setCurrentIndex(0)
        self._sc_show_send = True
        if hasattr(self, "_sc_show_send_cb"):
            self._sc_show_send_cb.setChecked(True)
        self._sc_line_by_line = False
        if hasattr(self, "_sc_line_by_line_cb"):
            self._sc_line_by_line_cb.setChecked(False)

        self._sc_send_history = []
        if hasattr(self, "_sc_history_combo"):
            self._sc_history_combo.blockSignals(True)
            self._sc_history_combo.clear()
            self._sc_history_combo.setCurrentIndex(-1)
            self._sc_history_combo.blockSignals(False)

        self._sc_sidebar_visible = True
        if hasattr(self, "_sc_sidebar_widget"):
            self._sc_sidebar_widget.setVisible(True)
        if hasattr(self, "_sc_sidebar_toggle_btn"):
            self._sc_sidebar_toggle_btn.setChecked(True)

        if hasattr(self, "_sc_center_splitter"):
            self._sc_center_splitter.setSizes(
                list(getattr(self, "_sc_center_splitter_default_sizes", [680, 155]))
            )

        if hasattr(self, "_sc_auto_baud_monitor"):
            self._sc_auto_baud_monitor.update_config(dict(AUTO_BAUD_CONFIG))
            self._sc_auto_baud_monitor.runtime_redetect_enabled = True

    def _sc_reset_user_config_keep_quick_commands(self, dialog_parent=None) -> bool:
        cfg_path = self._sc_persisted_path()
        ret = QMessageBox.question(
            dialog_parent or self,
            "Reset user config",
            "This will reset the user JSON to default settings, while keeping Quick Commands unchanged.\n\n"
            f"Before continuing, please back up this JSON file if needed:\n{cfg_path}\n\n"
            "Continue reset?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if ret != QMessageBox.Yes:
            return False

        quick_commands = getattr(self, "_sc_qc_data", self._sc_qc_default_data())
        scripts = getattr(self, "_sc_script_data", self._sc_script_default_data())
        reset_state = self._sc_default_persisted_state(
            quick_commands=quick_commands, scripts=scripts
        )
        try:
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(reset_state, f, ensure_ascii=False, indent=2)
            self._sc_window_geometry = None
            self._sc_apply_persisted_state(reset_state)
            self._sc_apply_reset_defaults_to_widgets()
            self._sc_skip_next_persist_save = True
            if hasattr(self, "_sc_append_system"):
                self._sc_append_system(f"[INFO] User config reset to defaults. Quick Commands kept. Path: {cfg_path}", force_primary=True)
            QMessageBox.information(
                dialog_parent or self,
                "Reset complete",
                "User JSON has been reset to default settings.\nQuick Commands were kept unchanged.",
            )
            if self.isWindow():
                QTimer.singleShot(0, self.close)
            return True
        except Exception as e:
            logger.error("Reset Serial Console config failed: %s", e, exc_info=True)
            QMessageBox.critical(dialog_parent or self, "Reset failed", f"Failed to reset config:\n{e}")
            return False

    def _sc_qc_save_data(self) -> None:
        self._sc_save_persisted_state()

    # --- log helpers ---

    _SC_MAX_LOG_LINES = 10000

    def _sc_start_temp_log(self):
        self._sc_close_temp_log(delete=True)
        import tempfile
        temp_dir = os.path.join(tempfile.gettempdir(), "kk_serial_logs")
        try:
            os.makedirs(temp_dir, exist_ok=True)
        except OSError:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"sc_temp_{ts}.txt"
        file_path = os.path.join(temp_dir, filename)
        try:
            self._sc_log_temp_handle = open(file_path, "a", encoding="utf-8")
            self._sc_log_temp_path = file_path
        except OSError:
            self._sc_log_temp_handle = None
            self._sc_log_temp_path = None

    def _sc_close_temp_log(self, delete: bool = False):
        if self._sc_log_temp_handle is not None:
            try:
                self._sc_log_temp_handle.close()
            except OSError:
                pass
            self._sc_log_temp_handle = None
        if delete and self._sc_log_temp_path:
            try:
                os.remove(self._sc_log_temp_path)
            except OSError:
                pass
            self._sc_log_temp_path = None

    def _sc_start_auto_save(self):
        if self._sc_log_file_handle is not None:
            return
        save_dir = getattr(self, '_sc_log_save_path', '')
        if not save_dir:
            save_dir = self._sc_fallback_dir()
        try:
            os.makedirs(save_dir, exist_ok=True)
        except OSError:
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        port = getattr(self, '_serial_port', '') or 'unknown'
        port_safe = re.sub(r'[^\w\-.]', '_', port)
        filename = f"serial_log_{port_safe}_{ts}.txt"
        file_path = os.path.join(save_dir, filename)
        try:
            self._sc_log_file_handle = open(file_path, "a", encoding="utf-8")
            self._sc_log_file_path = file_path
            self._sc_append_system(f"[INFO] Auto-save started: {file_path}", force_primary=True)
        except OSError:
            self._sc_log_file_handle = None
            self._sc_log_file_path = None

    def _sc_stop_auto_save(self):
        if self._sc_log_file_handle is not None:
            try:
                self._sc_log_file_handle.close()
            except OSError:
                pass
            self._sc_log_file_handle = None

    def _sc_write_to_log_files(self, raw: str):
        for fh_attr in ("_sc_log_temp_handle", "_sc_log_file_handle"):
            fh = getattr(self, fh_attr, None)
            if fh is not None:
                try:
                    fh.write(raw + "\n")
                    fh.flush()
                except OSError:
                    try:
                        fh.close()
                    except OSError:
                        pass
                    setattr(self, fh_attr, None)
        save_fh = getattr(self, "_sc_save_handle", None)
        if save_fh is not None:
            line = raw if self._sc_save_keep_timestamp else self._sc_strip_timestamp(raw)
            try:
                save_fh.write(line + "\n")
                save_fh.flush()
            except OSError:
                try:
                    save_fh.close()
                except OSError:
                    pass
                self._sc_save_handle = None
                if hasattr(self, "_sc_save_btn"):
                    self._sc_save_btn.setChecked(False)

    # --- NTP network time ---

    def _sc_start_ntp_sync(self):
        if self._sc_ntp_thread is not None:
            return
        self._sc_ntp_synced = False
        worker = _NtpSyncWorker()
        thread = QThread()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.synced.connect(self._sc_on_ntp_synced)
        worker.failed.connect(self._sc_on_ntp_failed)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._sc_ntp_thread = thread
        self._sc_ntp_worker = worker
        thread.start()

    def _sc_stop_ntp_sync(self):
        worker = getattr(self, "_sc_ntp_worker", None)
        thread = getattr(self, "_sc_ntp_thread", None)
        self._sc_ntp_worker = None
        self._sc_ntp_thread = None
        self._sc_ntp_synced = False
        if worker is not None:
            worker.stop()
        if thread is not None:
            thread.quit()
            thread.wait(2000)

    def _sc_on_ntp_synced(self, offset: float, rtt: float):
        self._sc_ntp_offset = offset
        self._sc_ntp_synced = True
        if hasattr(self, "_sc_append_system"):
            self._sc_append_system(
                f"[INFO] NTP synced: offset={offset * 1000:.1f} ms, rtt={rtt * 1000:.1f} ms",
                force_primary=True,
            )

    def _sc_on_ntp_failed(self, reason: str):
        self._sc_ntp_synced = False
        logger.warning("NTP sync failed: %s", reason)
        if hasattr(self, "_sc_append_system"):
            self._sc_append_system(f"[WARN] NTP sync failed: {reason}", force_primary=True)

    def _sc_ntp_timestamp(self):
        if not (self._sc_use_ntp and self._sc_ntp_synced):
            return ""
        ntp_dt = datetime.fromtimestamp(time.time() + self._sc_ntp_offset)
        return ntp_dt.strftime("%H:%M:%S.%f")[:-3]

    def _sc_apply_ntp_setting(self, enabled: bool):
        self._sc_use_ntp = bool(enabled)
        if self._sc_use_ntp:
            self._sc_start_ntp_sync()
        else:
            self._sc_stop_ntp_sync()

    def _sc_append_log(self, message: str, color: str = _CLR_TEXT_BODY):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3] if self._sc_show_timestamp else ""
        ntp_ts = self._sc_ntp_timestamp()
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        ts_html = f'<span style="color:{_CLR_TEXT_TIME};">{ts}</span> ' if ts else ""
        ntp_html = (
            f'<span style="color:{_CLR_TEXT_ACCENT};">[NTP]</span> '
            f'<span style="color:{_CLR_TEXT_TIME};">{ntp_ts}</span> '
            if ntp_ts else ""
        )
        html = f'{ts_html}{ntp_html}<span style="color:{color};">{escaped}</span>'
        prefix = ts
        if ntp_ts:
            prefix = f"{prefix} [NTP] {ntp_ts}" if prefix else f"[NTP] {ntp_ts}"
        raw = f"{prefix} {message}" if prefix else message
        self._sc_all_logs.append((raw, html))
        if len(self._sc_all_logs) > self._SC_MAX_LOG_LINES:
            self._sc_all_logs = self._sc_all_logs[-self._SC_MAX_LOG_LINES:]
        self._sc_write_to_log_files(raw)
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

    def _sc_append_system(self, message: str, force_primary: bool = False):
        color_map = {"INFO": _CLR_TEXT_INFO, "WARN": _CLR_WARNING, "ERROR": _CLR_ERROR}
        tag = ""
        for t in color_map:
            if f"[{t}]" in message:
                tag = t
                break
        color = color_map.get(tag, _CLR_TEXT_INFO)
        if not force_primary and self._sc_active_log_panel_index > 0:
            panel_idx = self._sc_active_log_panel_index - 1
            if 0 <= panel_idx < len(self._sc_extra_log_panels):
                self._sc_extra_panel_append_log(
                    self._sc_extra_log_panels[panel_idx], message, color
                )
                return
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
            icon_color = _CLR_TEXT_BTN_LOG
            btn.setStyleSheet(log_toolbar_button_style())
        elif tone == "quick":
            icon_color = _CLR_TEXT_BTN_LOG
            btn.setStyleSheet(quick_toolbar_button_style(max_height=26, padding="4px 11px", radius=6, min_height=0))
        else:
            icon_color = _CLR_TEXT_MUTED
            icon_size = 13
            btn.setStyleSheet(transparent_toolbar_button_style())
        icon = _tinted_svg_icon(svg_path, icon_color, icon_size)
        if not icon.isNull():
            btn.setIcon(icon)
        return btn

    @staticmethod
    def _make_sc_section(title):
        grp = QFrame()
        grp.setObjectName("scSectionCard")
        grp.setStyleSheet(section_card_style())
        layout = QVBoxLayout(grp)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        lbl = QLabel(title)
        lbl.setStyleSheet(section_title_style())
        layout.addWidget(lbl)

        grp.setProperty("_inner_layout", layout)
        return grp

    @staticmethod
    def _make_sc_label(text):
        lbl = QLabel(text)
        lbl.setStyleSheet(field_label_style())
        return lbl

    @staticmethod
    def _sc_checkbox_style():
        _chk_svg = os.path.join(_SVG_SERIAL_DIR, "checkmark.svg").replace("\\", "/")
        return checkbox_style(_chk_svg)


class _MiniSlideToggle(QWidget):
    toggled = Signal(str)

    def __init__(self, left="ASCII", right="HEX", parent=None):
        super().__init__(parent)
        self._left = left
        self._right = right
        self._value = left
        self._anim_progress = 0.0

        self.setFixedSize(SerialComMixin._TOGGLE_W, 24)
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

        colors = toggle_colors()
        p.setPen(QPen(QColor(colors["border"]), 1))
        p.setBrush(QColor(colors["background"]))
        p.drawRoundedRect(QRectF(0, 0, w, h), outer_r, outer_r)

        knob_margin = 2
        knob_h = h - knob_margin * 2
        knob_w = w / 2 - knob_margin
        knob_x = knob_margin + self._anim_progress * (w / 2)
        knob_r = 3

        p.setPen(Qt.NoPen)
        p.setBrush(QColor(colors["knob"]))
        p.drawRoundedRect(QRectF(knob_x, knob_margin, knob_w, knob_h),
                          knob_r, knob_r)

        font = p.font()
        font.setPixelSize(10)
        font.setWeight(QFont.Bold)
        p.setFont(font)

        left_rect = QRectF(0, 0, w / 2, h)
        right_rect = QRectF(w / 2, 0, w / 2, h)

        p.setPen(QColor(colors["active_text"]) if self._anim_progress < 0.5 else QColor(colors["inactive_text"]))
        p.drawText(left_rect, Qt.AlignCenter, self._left)

        p.setPen(QColor(colors["active_text"]) if self._anim_progress >= 0.5 else QColor(colors["inactive_text"]))
        p.drawText(right_rect, Qt.AlignCenter, self._right)

        p.end()


class _AddLogPanelDialog(QDialog):

    def __init__(self, panel_index: int = 2, parent=None):
        super().__init__(parent)
        self._panel_index = panel_index
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
        self._title_edit.setText(f"Serial Log {self._panel_index}")
        self._title_edit.setStyleSheet(dialog_line_edit_style())
        grid.addWidget(self._title_edit, 0, 1)

        grid.addWidget(QLabel("Port"), 1, 0)
        self._port_combo = SerialDarkComboBox()
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
        self._baud_combo = SerialDarkComboBox()
        self._baud_combo.setFixedHeight(26)
        self._baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000"]:
            self._baud_combo.addItem(br)
        self._baud_combo.setCurrentIndex(0)
        grid.addWidget(self._baud_combo, 2, 1)

        grid.addWidget(QLabel("Data bits"), 3, 0)
        self._databit_combo = SerialDarkComboBox()
        self._databit_combo.setFixedHeight(26)
        for d in ["8", "7", "6", "5"]:
            self._databit_combo.addItem(d)
        grid.addWidget(self._databit_combo, 3, 1)

        grid.addWidget(QLabel("Stop bits"), 4, 0)
        self._stopbit_combo = SerialDarkComboBox()
        self._stopbit_combo.setFixedHeight(26)
        for s in ["1", "1.5", "2"]:
            self._stopbit_combo.addItem(s)
        grid.addWidget(self._stopbit_combo, 4, 1)

        grid.addWidget(QLabel("Parity"), 5, 0)
        self._parity_combo = SerialDarkComboBox()
        self._parity_combo.setFixedHeight(26)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._parity_combo.addItem(p)
        grid.addWidget(self._parity_combo, 5, 1)

        grid.addWidget(QLabel("Flow Control"), 6, 0)
        self._flow_combo = SerialDarkComboBox()
        self._flow_combo.setFixedHeight(26)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._flow_combo.addItem(fc)
        grid.addWidget(self._flow_combo, 6, 1)

        root.addLayout(grid)

        mode_grp = QHBoxLayout()
        mode_grp.setSpacing(16)
        mode_label = QLabel("Open in:")
        mode_grp.addWidget(mode_label)
        from PySide6.QtWidgets import QRadioButton, QButtonGroup
        self._mode_same_window = QRadioButton("Same Window")
        self._mode_same_window.setChecked(True)
        self._mode_independent = QRadioButton("Independent Window")
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self._mode_same_window, 0)
        self._mode_group.addButton(self._mode_independent, 1)
        mode_grp.addWidget(self._mode_same_window)
        mode_grp.addWidget(self._mode_independent)
        mode_grp.addStretch()
        root.addLayout(mode_grp)

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
            "independent_window": self._mode_independent.isChecked(),
        }


class _PanelSettingsDialog(QDialog):

    def __init__(self, current_config: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Panel Settings")
        self.setFixedWidth(400)
        self.setStyleSheet(_DLG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("Serial Port Settings")
        title.setObjectName("dlgSectionTitle")
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Panel Name"), 0, 0)
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("e.g. LOG-2")
        self._title_edit.setText(current_config.get("title", "Serial Log"))
        self._title_edit.setStyleSheet(dialog_line_edit_style())
        grid.addWidget(self._title_edit, 0, 1)

        grid.addWidget(QLabel("Port"), 1, 0)
        self._port_combo = SerialDarkComboBox()
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
        cur_port = current_config.get("port", "")
        if cur_port:
            for i in range(self._port_combo.count()):
                if self._port_combo.itemText(i).startswith(cur_port):
                    self._port_combo.setCurrentIndex(i)
                    break
            else:
                self._port_combo.setEditText(cur_port)
        grid.addWidget(self._port_combo, 1, 1)

        grid.addWidget(QLabel("Baudrate"), 2, 0)
        self._baud_combo = SerialDarkComboBox()
        self._baud_combo.setFixedHeight(26)
        self._baud_combo.setEditable(True)
        for br in ["921600", "1152000", "2000000", "3000000", "115200", "9600"]:
            self._baud_combo.addItem(br)
        cur_baud = str(current_config.get("baudrate", 921600))
        idx = self._baud_combo.findText(cur_baud)
        if idx >= 0:
            self._baud_combo.setCurrentIndex(idx)
        else:
            self._baud_combo.setEditText(cur_baud)
        grid.addWidget(self._baud_combo, 2, 1)

        grid.addWidget(QLabel("Data bits"), 3, 0)
        self._databit_combo = SerialDarkComboBox()
        self._databit_combo.setFixedHeight(26)
        for d in ["8", "7", "6", "5"]:
            self._databit_combo.addItem(d)
        cur_databit = str(current_config.get("databit", 8))
        idx = self._databit_combo.findText(cur_databit)
        if idx >= 0:
            self._databit_combo.setCurrentIndex(idx)
        grid.addWidget(self._databit_combo, 3, 1)

        grid.addWidget(QLabel("Stop bits"), 4, 0)
        self._stopbit_combo = SerialDarkComboBox()
        self._stopbit_combo.setFixedHeight(26)
        for s in ["1", "1.5", "2"]:
            self._stopbit_combo.addItem(s)
        cur_stopbit = str(current_config.get("stopbit", "1"))
        idx = self._stopbit_combo.findText(cur_stopbit)
        if idx >= 0:
            self._stopbit_combo.setCurrentIndex(idx)
        grid.addWidget(self._stopbit_combo, 4, 1)

        grid.addWidget(QLabel("Parity"), 5, 0)
        self._parity_combo = SerialDarkComboBox()
        self._parity_combo.setFixedHeight(26)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self._parity_combo.addItem(p)
        cur_parity = current_config.get("parity", "None")
        idx = self._parity_combo.findText(cur_parity)
        if idx >= 0:
            self._parity_combo.setCurrentIndex(idx)
        grid.addWidget(self._parity_combo, 5, 1)

        grid.addWidget(QLabel("Flow Control"), 6, 0)
        self._flow_combo = SerialDarkComboBox()
        self._flow_combo.setFixedHeight(26)
        for fc in ["None", "RTS/CTS", "XON/XOFF"]:
            self._flow_combo.addItem(fc)
        cur_flow = current_config.get("flow", "None")
        idx = self._flow_combo.findText(cur_flow)
        if idx >= 0:
            self._flow_combo.setCurrentIndex(idx)
        grid.addWidget(self._flow_combo, 6, 1)

        root.addLayout(grid)

        self._auto_connect_cb = QCheckBox("Auto connect after apply")
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

        ok_btn = QPushButton("Apply")
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


class _IndependentSerialWindow(QWidget):

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._config = config
        self._conn = None
        self._read_thread = None
        self._read_worker = None
        self._rx_bytes = 0
        self._tx_bytes = 0
        self._auto_scroll = True

        title = config.get("title", "Serial Log")
        self.setWindowTitle(f"Serial Console - {title}")
        self.setMinimumSize(600, 400)
        self.resize(750, 500)
        self.setStyleSheet(f"background-color: {_CLR_BG_LOG}; color: {_CLR_INPUT_TEXT};")

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        port_text = config.get("port", "N/A")
        baud_text = str(config.get("baudrate", "N/A"))
        self._status_label = QLabel(f"{port_text} @ {baud_text}")
        self._status_label.setStyleSheet(f"color: {_CLR_TEXT_MUTED}; font-size: 12px;")
        toolbar.addWidget(self._status_label)

        toolbar.addStretch()

        self._connect_btn = QPushButton("Connect")
        self._connect_btn.setCursor(Qt.PointingHandCursor)
        self._connect_btn.clicked.connect(self._toggle_connect)
        toolbar.addWidget(self._connect_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_log)
        toolbar.addWidget(clear_btn)

        root.addLayout(toolbar)

        self._log_edit = QTextEdit()
        self._log_edit.setReadOnly(True)
        self._log_edit.setStyleSheet(log_edit_style(padding="6px 8px") + SERIAL_SCROLLBAR_STYLE)
        self._log_edit.document().setDefaultStyleSheet(log_document_style())
        self._log_edit.document().setMaximumBlockCount(5000)
        root.addWidget(self._log_edit, 1)

        send_row = QHBoxLayout()
        send_row.setSpacing(4)
        self._send_input = QLineEdit()
        self._send_input.setPlaceholderText("Enter command...")
        self._send_input.setStyleSheet(filter_input_style())
        self._send_input.returnPressed.connect(self._on_send)
        send_row.addWidget(self._send_input, 1)
        send_btn = QPushButton("Send")
        send_btn.setCursor(Qt.PointingHandCursor)
        send_btn.clicked.connect(self._on_send)
        send_row.addWidget(send_btn)
        root.addLayout(send_row)

        status_bar = QHBoxLayout()
        self._rx_label = QLabel("RX: 0 B")
        self._rx_label.setStyleSheet(f"color: {_CLR_TEXT_MUTED}; font-size: 11px;")
        self._tx_label = QLabel("TX: 0 B")
        self._tx_label.setStyleSheet(f"color: {_CLR_TEXT_MUTED}; font-size: 11px;")
        status_bar.addWidget(self._rx_label)
        status_bar.addWidget(self._tx_label)
        status_bar.addStretch()
        root.addLayout(status_bar)

        if config.get("auto_connect", False):
            from PySide6.QtCore import QTimer
            QTimer.singleShot(200, self._do_connect)

    def _toggle_connect(self):
        if DEBUG_MOCK and self._connect_btn.text() == "Disconnect":
            self._do_disconnect()
        elif self._conn is not None and self._conn.is_open:
            self._do_disconnect()
        else:
            self._do_connect()

    def _do_connect(self):
        port = self._config.get("port", "")
        baudrate = self._config.get("baudrate", 115200)
        if not port:
            self._append("[ERROR] No port configured")
            return

        if DEBUG_MOCK:
            self._conn = None
            self._connect_btn.setText("Disconnect")
            self._status_label.setText(f"MOCK @ {baudrate}")
            self._status_label.setStyleSheet(f"color: {_CLR_CONNECT_FG}; font-size: 12px;")
            self._append(f"[INFO] Mock connected: {port} @ {baudrate}")
            return

        try:
            databit = self._config.get("databit", 8)
            stopbit_map = {"1": serial.STOPBITS_ONE, "1.5": serial.STOPBITS_ONE_POINT_FIVE, "2": serial.STOPBITS_TWO}
            stopbits = stopbit_map.get(str(self._config.get("stopbit", "1")), serial.STOPBITS_ONE)
            parity_map = {"None": serial.PARITY_NONE, "Even": serial.PARITY_EVEN, "Odd": serial.PARITY_ODD}
            parity = parity_map.get(self._config.get("parity", "None"), serial.PARITY_NONE)
            flow = self._config.get("flow", "None")
            conn = serial.Serial(
                port=port, baudrate=baudrate, bytesize=databit,
                stopbits=stopbits, parity=parity,
                xonxoff=(flow == "XON/XOFF"), rtscts=(flow == "RTS/CTS"),
                timeout=0.1,
            )
            self._conn = conn
            self._connect_btn.setText("Disconnect")
            self._status_label.setText(f"{port} @ {baudrate}")
            self._status_label.setStyleSheet(f"color: {_CLR_CONNECT_FG}; font-size: 12px;")
            self._append(f"[INFO] Connected: {port} @ {baudrate}")
            self._start_read()
        except Exception as e:
            self._append(f"[ERROR] Connection failed: {e}")

    def _do_disconnect(self):
        self._stop_read()
        try:
            if self._conn is not None and self._conn.is_open:
                self._conn.close()
        except Exception:
            pass
        self._conn = None
        self._connect_btn.setText("Connect")
        self._status_label.setStyleSheet(f"color: {_CLR_TEXT_MUTED}; font-size: 12px;")
        self._append("[INFO] Disconnected")

    def _on_send(self):
        text = self._send_input.text()
        if not text:
            return
        data = (text + "\r\n").encode("utf-8")

        if DEBUG_MOCK:
            self._tx_bytes += len(data)
            self._tx_label.setText(f"TX: {self._tx_bytes} B")
            self._append(f"[TX] {text}")
            self._send_input.clear()
            return

        if self._conn is None or not self._conn.is_open:
            self._append("[ERROR] Not connected")
            return
        try:
            self._conn.write(data)
            self._tx_bytes += len(data)
            self._tx_label.setText(f"TX: {self._tx_bytes} B")
            self._append(f"[TX] {text}")
            self._send_input.clear()
        except Exception as e:
            self._append(f"[ERROR] Send failed: {e}")

    def _clear_log(self):
        self._log_edit.clear()
        self._rx_bytes = 0
        self._tx_bytes = 0
        self._rx_label.setText("RX: 0 B")
        self._tx_label.setText("TX: 0 B")

    def _append(self, message):
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%H:%M:%S.%f")[:-3]
        color = _CLR_TEXT_BODY
        if "[ERROR]" in message:
            color = _CLR_ERROR
        elif "[INFO]" in message:
            color = _CLR_TEXT_INFO
        elif "[TX]" in message:
            color = _CLR_TX
        elif "[RX]" in message:
            color = _CLR_RX
        escaped = message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        html = f'<span style="color:{_CLR_TEXT_TIME};">{ts}</span> <span style="color:{color};">{escaped}</span>'
        self._log_edit.append(html)
        if self._auto_scroll:
            sb = self._log_edit.verticalScrollBar()
            if sb:
                sb.setValue(sb.maximum())

    def _start_read(self):
        if self._conn is None:
            return
        worker = _SerialReadWorker(self._conn)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.data_received.connect(self._on_data_received)
        self._read_thread = thread
        self._read_worker = worker
        thread.start()

    def _stop_read(self):
        if self._read_worker:
            self._read_worker.stop()
        if self._read_thread and self._read_thread.isRunning():
            self._read_thread.quit()
            self._read_thread.wait(3000)
        self._read_thread = None
        self._read_worker = None

    def _on_data_received(self, data: bytes):
        self._rx_bytes += len(data)
        self._rx_label.setText(f"RX: {self._rx_bytes} B")
        try:
            text = data.decode("utf-8", errors="replace")
            for line in text.splitlines():
                if line.strip():
                    self._append(f"[RX] {line}")
        except Exception:
            self._append(f"[RX] {data.hex(' ')}")

    def closeEvent(self, event):
        self._sc_stop_ntp_sync()
        self._do_disconnect()
        super().closeEvent(event)


class _QuickCmdPreviewPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setObjectName("quickCmdPreviewPopupWindow")
        self._card = QFrame(self)
        self._card.setObjectName("quickCmdPreviewPopup")
        self._badge_label = QLabel("QUICK CMD")
        self._badge_label.setObjectName("quickCmdPreviewBadge")
        self._title_label = QLabel()
        self._title_label.setObjectName("quickCmdPreviewTitle")
        self._title_label.setTextFormat(Qt.PlainText)
        self._content_label = QLabel()
        self._content_label.setObjectName("quickCmdPreviewContent")
        self._content_label.setWordWrap(True)
        self._content_label.setTextFormat(Qt.PlainText)
        self._content_label.setTextInteractionFlags(Qt.NoTextInteraction)
        self._meta_label = QLabel()
        self._meta_label.setObjectName("quickCmdPreviewMeta")
        self._meta_label.setWordWrap(True)
        self._meta_label.setTextFormat(Qt.PlainText)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(7)
        header_layout.addWidget(self._badge_label, 0, Qt.AlignVCenter)
        header_layout.addWidget(self._title_label, 1, Qt.AlignVCenter)
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(6)
        card_layout.addLayout(header_layout)
        card_layout.addWidget(self._content_label)
        card_layout.addWidget(self._meta_label)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(0)
        layout.addWidget(self._card)
        shadow_style = quick_preview_popup_shadow()
        shadow = QGraphicsDropShadowEffect(self._card)
        shadow.setBlurRadius(shadow_style["blur_radius"])
        shadow.setOffset(shadow_style["offset_x"], shadow_style["offset_y"])
        shadow.setColor(QColor(*shadow_style["color"]))
        self._card.setGraphicsEffect(shadow)
        self.setStyleSheet(quick_preview_popup_style())

    def set_preview_data(self, name: str, content: str, send_type: str, encoding: str, line_ending: str):
        display_name = str(name or "Untitled")
        display_content = str(content or "")
        display_type = str(send_type or "text")
        display_encoding = str(encoding or "ascii")
        display_line_ending = repr(line_ending or "")
        if len(display_content) > 360:
            display_content = f"{display_content[:360]}..."
        self._title_label.setText(display_name)
        self._content_label.setText(display_content if display_content else " ")
        self._meta_label.setText(
            f"Type: {display_type}   Encoding: {display_encoding}   Line: {display_line_ending}"
        )
        self.setFixedWidth(368)
        self.adjustSize()


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
        self._preview_data = None
        self._preview_popup = _QuickCmdPreviewPopup()
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(80)
        self._preview_timer.timeout.connect(self._show_preview)

    def set_command_index(self, idx: int):
        self._cmd_index = idx

    def command_index(self) -> int:
        return self._cmd_index

    def set_preview_data(self, name: str, content: str, send_type: str, encoding: str, line_ending: str):
        self._preview_data = {
            "name": name,
            "content": content,
            "send_type": send_type,
            "encoding": encoding,
            "line_ending": line_ending,
        }

    def enterEvent(self, event):
        super().enterEvent(event)
        self._preview_timer.start()

    def leaveEvent(self, event):
        self._preview_timer.stop()
        self._preview_popup.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._preview_popup.hide()
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
                self._preview_timer.stop()
                self._preview_popup.hide()
                self._dragging = True
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def _show_preview(self):
        if not self._preview_data or self._dragging or not self.underMouse():
            return
        self._preview_popup.set_preview_data(**self._preview_data)
        self._preview_popup.ensurePolished()
        pos = self._bounded_preview_pos()
        self._preview_popup.move(pos)
        self._preview_popup.show()

    def _bounded_preview_pos(self) -> QPoint:
        pos = self.mapToGlobal(QPoint(0, self.height() + 8))
        popup_size = self._preview_popup.sizeHint()
        screen = QApplication.screenAt(pos) or self.screen() or QApplication.primaryScreen()
        if screen is None:
            return pos
        available = screen.availableGeometry()
        safe_margin = 24
        x = min(
            max(pos.x(), available.left() + safe_margin),
            available.right() - popup_size.width() - safe_margin,
        )
        y = pos.y()
        if y + popup_size.height() + safe_margin > available.bottom():
            y = self.mapToGlobal(QPoint(0, -popup_size.height() - 8)).y()
        y = min(
            max(y, available.top() + safe_margin),
            available.bottom() - popup_size.height() - safe_margin,
        )
        return QPoint(x, y)

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


class _SerialScriptEditorDialog(QDialog):
    _COLS = ["指令", "优先级", "等待(ms)", "类型", "结尾符", "等待关键字", "关键字超时(ms)"]

    def __init__(self, parent=None, script: dict = None):
        super().__init__(parent)
        self.setWindowTitle("脚本编辑器")
        self.setMinimumSize(720, 460)
        self.setStyleSheet(_DLG_STYLE)
        script = script or {}

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(14)

        title = QLabel("编辑脚本")
        title.setObjectName("qcTitle")
        root.addWidget(title)

        # --- 脚本属性卡片 ---
        prop_card = QFrame()
        prop_card.setObjectName("dlgGroupCard")
        prop_form = QVBoxLayout(prop_card)
        prop_form.setContentsMargins(14, 12, 14, 12)
        prop_form.setSpacing(8)

        prop_row = QHBoxLayout()
        prop_row.setSpacing(8)
        name_lbl = QLabel("脚本名称")
        name_lbl.setObjectName("dlgFieldLabel")
        prop_row.addWidget(name_lbl)
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如：WiFi 压测")
        self._name_edit.setText(script.get("name", ""))
        prop_row.addWidget(self._name_edit, 1)

        self._loop_cb = QCheckBox("循环")
        self._loop_cb.setChecked(bool(script.get("loop", False)))
        prop_row.addWidget(self._loop_cb)

        count_lbl = QLabel("次数")
        count_lbl.setObjectName("dlgFieldLabel")
        prop_row.addWidget(count_lbl)
        self._loop_spin = QSpinBox()
        self._loop_spin.setRange(1, 99999)
        self._loop_spin.setValue(int(script.get("loop_count", 1)) or 1)
        prop_row.addWidget(self._loop_spin)
        prop_form.addLayout(prop_row)

        hint = QLabel("提示：优先级=0 表示跳过该步；其余按从小到大顺序执行。设置“等待关键字”后将先等待收到该字符串，超时后继续。")
        hint.setWordWrap(True)
        hint.setObjectName("dlgHint")
        prop_form.addWidget(hint)
        root.addWidget(prop_card)

        # --- 步骤区：标题 + 行操作 ---
        steps_head = QHBoxLayout()
        steps_head.setSpacing(8)
        steps_title = QLabel("执行步骤")
        steps_title.setObjectName("dlgSectionTitle")
        steps_head.addWidget(steps_title)
        steps_head.addStretch()

        add_btn = QPushButton("+ 添加步骤")
        add_btn.setObjectName("dlgRowBtn")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(lambda: self._add_row())
        steps_head.addWidget(add_btn)

        del_btn = QPushButton("- 删除选中")
        del_btn.setObjectName("dlgRowBtn")
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.clicked.connect(self._del_row)
        steps_head.addWidget(del_btn)

        up_btn = QPushButton("↑ 上移")
        up_btn.setObjectName("dlgRowBtn")
        up_btn.setCursor(Qt.PointingHandCursor)
        up_btn.clicked.connect(lambda: self._move_row(-1))
        steps_head.addWidget(up_btn)

        down_btn = QPushButton("↓ 下移")
        down_btn.setObjectName("dlgRowBtn")
        down_btn.setCursor(Qt.PointingHandCursor)
        down_btn.clicked.connect(lambda: self._move_row(1))
        steps_head.addWidget(down_btn)

        renum_btn = QPushButton("重排优先级")
        renum_btn.setObjectName("dlgRowBtn")
        renum_btn.setCursor(Qt.PointingHandCursor)
        renum_btn.clicked.connect(self._renumber_priority)
        steps_head.addWidget(renum_btn)
        root.addLayout(steps_head)

        # --- 步骤表 ---
        self._table = QTableWidget(0, len(self._COLS))
        self._table.setObjectName("dlgStepTable")
        self._table.setHorizontalHeaderLabels(self._COLS)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)
        self._table.setWordWrap(False)
        self._table.verticalHeader().setDefaultSectionSize(40)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        hdr = self._table.horizontalHeader()
        hdr.setMinimumSectionSize(72)
        hdr.setHighlightSections(False)
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(5, QHeaderView.Stretch)
        for c in (1, 2, 3, 4, 6):
            hdr.setSectionResizeMode(c, QHeaderView.Fixed)
        self._table.setColumnWidth(1, 84)
        self._table.setColumnWidth(2, 104)
        self._table.setColumnWidth(3, 92)
        self._table.setColumnWidth(4, 92)
        self._table.setColumnWidth(6, 128)
        root.addWidget(self._table, 1)

        for step in script.get("steps", []):
            self._add_row(step)
        if self._table.rowCount() == 0:
            self._add_row()

        # --- OK / Cancel ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(dialog_cancel_button_style())
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

        self._script_id = script.get("id", "")

    def _wrap_cell(self, widget) -> QWidget:
        holder = QWidget()
        lay = QHBoxLayout(holder)
        lay.setContentsMargins(6, 4, 6, 4)
        lay.setSpacing(0)
        lay.addWidget(widget)
        return holder

    def _add_row(self, step: dict = None):
        step = step or {
            "cmd": "", "priority": self._table.rowCount() + 1, "wait_ms": 1000,
            "send_type": "text", "line_ending": "\r\n",
            "wait_keyword": "", "wait_timeout_ms": 0,
        }
        row = self._table.rowCount()
        self._table.insertRow(row)

        cmd_item = QTableWidgetItem(step.get("cmd", ""))
        cmd_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._table.setItem(row, 0, cmd_item)

        prio_spin = QSpinBox()
        prio_spin.setRange(0, 9999)
        prio_spin.setValue(int(step.get("priority", row + 1)))
        self._table.setCellWidget(row, 1, self._wrap_cell(prio_spin))

        wait_spin = QSpinBox()
        wait_spin.setRange(0, 3600000)
        wait_spin.setSingleStep(100)
        wait_spin.setValue(int(step.get("wait_ms", 1000)))
        self._table.setCellWidget(row, 2, self._wrap_cell(wait_spin))

        type_combo = QComboBox()
        type_combo.addItem("TEXT", "text")
        type_combo.addItem("HEX", "hex")
        ti = type_combo.findData(step.get("send_type", "text"))
        type_combo.setCurrentIndex(ti if ti >= 0 else 0)
        self._table.setCellWidget(row, 3, self._wrap_cell(type_combo))

        le_combo = QComboBox()
        le_combo.addItem("无", "")
        le_combo.addItem("\\r", "\r")
        le_combo.addItem("\\n", "\n")
        le_combo.addItem("\\r\\n", "\r\n")
        li = le_combo.findData(step.get("line_ending", "\r\n"))
        le_combo.setCurrentIndex(li if li >= 0 else 3)
        self._table.setCellWidget(row, 4, self._wrap_cell(le_combo))

        kw_item = QTableWidgetItem(step.get("wait_keyword", ""))
        kw_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._table.setItem(row, 5, kw_item)

        to_spin = QSpinBox()
        to_spin.setRange(0, 3600000)
        to_spin.setSingleStep(100)
        to_spin.setValue(int(step.get("wait_timeout_ms", 0)))
        self._table.setCellWidget(row, 6, self._wrap_cell(to_spin))

    def _del_row(self):
        row = self._table.currentRow()
        if row >= 0:
            self._table.removeRow(row)

    def _move_row(self, delta: int):
        row = self._table.currentRow()
        if row < 0:
            return
        target = row + delta
        if target < 0 or target >= self._table.rowCount():
            return
        steps = self._collect_steps()
        steps[row], steps[target] = steps[target], steps[row]
        self._reload_steps(steps)
        self._table.setCurrentCell(target, 0)

    def _inner_widget(self, row: int, col: int):
        holder = self._table.cellWidget(row, col)
        if holder is None:
            return None
        lay = holder.layout()
        if lay is not None and lay.count() > 0:
            return lay.itemAt(0).widget()
        return holder

    def _renumber_priority(self):
        for row in range(self._table.rowCount()):
            spin = self._inner_widget(row, 1)
            if isinstance(spin, QSpinBox):
                spin.setValue(row + 1)

    def _reload_steps(self, steps: list):
        self._table.setRowCount(0)
        for step in steps:
            self._add_row(step)

    def _collect_steps(self) -> list:
        steps = []
        for row in range(self._table.rowCount()):
            cmd_item = self._table.item(row, 0)
            kw_item = self._table.item(row, 5)
            prio = self._inner_widget(row, 1)
            wait = self._inner_widget(row, 2)
            tcombo = self._inner_widget(row, 3)
            lcombo = self._inner_widget(row, 4)
            to = self._inner_widget(row, 6)
            steps.append({
                "cmd": cmd_item.text() if cmd_item else "",
                "priority": prio.value() if isinstance(prio, QSpinBox) else row + 1,
                "wait_ms": wait.value() if isinstance(wait, QSpinBox) else 0,
                "send_type": tcombo.currentData() if isinstance(tcombo, QComboBox) else "text",
                "line_ending": lcombo.currentData() if isinstance(lcombo, QComboBox) else "\r\n",
                "wait_keyword": kw_item.text() if kw_item else "",
                "wait_timeout_ms": to.value() if isinstance(to, QSpinBox) else 0,
            })
        return steps

    def _on_accept(self):
        if not self._name_edit.text().strip():
            QMessageBox.warning(self, "提示", "请填写脚本名称")
            return
        steps = [s for s in self._collect_steps() if s["cmd"].strip()]
        if not steps:
            QMessageBox.warning(self, "提示", "至少需要一个有内容的步骤")
            return
        self.accept()

    def get_script(self) -> dict:
        return {
            "id": self._script_id,
            "name": self._name_edit.text().strip(),
            "loop": self._loop_cb.isChecked(),
            "loop_count": self._loop_spin.value(),
            "steps": [s for s in self._collect_steps() if s["cmd"].strip()],
        }


class _QuickCmdDialog(QDialog):

    def __init__(self, parent=None, name="", content="", send_type="text",
                 line_ending="\r\n", encoding="ascii"):
        super().__init__(parent)
        self.setWindowTitle("Quick Command")
        self.setFixedWidth(380)
        self.setStyleSheet(quick_cmd_dialog_style())

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
        cancel_btn.setStyleSheet(dialog_cancel_button_style())
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
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


class _SerialSaveDialog(QDialog):

    def __init__(self, parent=None, default_dir="", default_name="", keep_timestamp=True):
        super().__init__(parent)
        self.setWindowTitle("Save Logs")
        self.setFixedWidth(440)
        self.setStyleSheet(quick_cmd_dialog_style())

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("保存日志")
        title.setObjectName("qcTitle")
        root.addWidget(title)

        root.addWidget(QLabel("保存位置"))
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        self._dir_edit = QLineEdit()
        self._dir_edit.setPlaceholderText("选择保存目录")
        self._dir_edit.setText(default_dir)
        dir_row.addWidget(self._dir_edit, 1)
        browse_btn = QPushButton("浏览…")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setStyleSheet(dialog_cancel_button_style())
        browse_btn.setAutoDefault(False)
        browse_btn.setDefault(False)
        browse_btn.clicked.connect(self._on_browse)
        dir_row.addWidget(browse_btn)
        root.addLayout(dir_row)

        root.addWidget(QLabel("文件名"))
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("如:serial_log.txt")
        self._name_edit.setText(default_name)
        root.addWidget(self._name_edit)

        self._keep_ts_cb = QCheckBox("保留系统时间戳（每行前缀 HH:MM:SS.fff）")
        self._keep_ts_cb.setChecked(keep_timestamp)
        root.addWidget(self._keep_ts_cb)

        hint = QLabel("点击保存后将写入当前完整日志，并持续追加后续新日志。")
        hint.setWordWrap(True)
        root.addWidget(hint)

        root.addSpacing(4)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(dialog_cancel_button_style())
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("Save")
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet(dialog_ok_button_style())
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)
        root.addLayout(btn_row)

    def _on_browse(self):
        current = self._dir_edit.text().strip()
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", current)
        if directory:
            self._dir_edit.setText(directory)

    def get_config(self) -> dict:
        return {
            "directory": self._dir_edit.text().strip(),
            "name": self._name_edit.text().strip(),
            "keep_timestamp": self._keep_ts_cb.isChecked(),
        }


class _SerialSettingsDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Serial Settings")
        self.setMinimumSize(720, 500)
        self.resize(760, 540)
        self.setStyleSheet(_DLG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        self._tabs = QTabWidget()
        self._tabs.setUsesScrollButtons(False)
        self._tabs.tabBar().setExpanding(False)
        root.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_tab_serial(), "Serial")
        self._tabs.addTab(self._build_tab_rx(), "RX")
        self._tabs.addTab(self._build_tab_tx(), "TX")
        self._tabs.addTab(self._build_tab_log(), "Log")
        self._tabs.addTab(self._build_tab_display(), "Display")
        self._tabs.addTab(self._build_tab_auto_detect(), "Auto-Detect")
        self._tabs.addTab(self._build_tab_about(), "About")

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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("Connection"))

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Port"), 0, 0)
        self.port_combo = SerialDarkComboBox()
        self.port_combo.setFixedHeight(26)
        grid.addWidget(self.port_combo, 0, 1)

        grid.addWidget(QLabel("Baudrate"), 1, 0)
        self.baud_combo = SerialDarkComboBox()
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
        self.databit_combo = SerialDarkComboBox()
        self.databit_combo.setFixedHeight(26)
        for d in ["8", "7", "6", "5"]:
            self.databit_combo.addItem(d)
        adv_grid.addWidget(self.databit_combo, 0, 1)

        adv_grid.addWidget(QLabel("Stop bits"), 0, 2)
        self.stopbit_combo = SerialDarkComboBox()
        self.stopbit_combo.setFixedHeight(26)
        for s in ["1", "1.5", "2"]:
            self.stopbit_combo.addItem(s)
        adv_grid.addWidget(self.stopbit_combo, 0, 3)

        adv_grid.addWidget(QLabel("Parity"), 1, 0)
        self.parity_combo = SerialDarkComboBox()
        self.parity_combo.setFixedHeight(26)
        for p in ["None", "Even", "Odd", "Mark", "Space"]:
            self.parity_combo.addItem(p)
        adv_grid.addWidget(self.parity_combo, 1, 1)

        adv_grid.addWidget(QLabel("Flow Control"), 1, 2)
        self.flow_combo = SerialDarkComboBox()
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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("Data Format"))

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(QLabel("Encoding"))
        self.tx_hex_toggle = _MiniSlideToggle("ASCII", "HEX")
        row.addWidget(self.tx_hex_toggle)
        row.addStretch()
        layout.addLayout(row)

        layout.addWidget(self._separator())
        layout.addWidget(self._section_title("Line Ending"))

        ending_row = QHBoxLayout()
        ending_row.setSpacing(8)
        ending_row.addWidget(QLabel("Line ending"))
        self.ending_combo = SerialDarkComboBox()
        self.ending_combo.setFixedHeight(26)
        for label, val in [("\\r\\n", "\r\n"), ("\\n", "\n"), ("\\r", "\r"), ("\\n\\r", "\n\r"), ("None", "")]:
            self.ending_combo.addItem(label, val)
        ending_row.addWidget(self.ending_combo)
        ending_row.addStretch()
        layout.addLayout(ending_row)

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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("Log File"))

        self.log_auto_save_cb = QCheckBox("Auto save log to file")
        layout.addWidget(self.log_auto_save_cb)

        path_row = QHBoxLayout()
        path_row.setSpacing(6)
        path_row.addWidget(QLabel("Save path"))
        self.log_save_path_edit = QLineEdit()
        self.log_save_path_edit.setPlaceholderText("Select log save directory...")
        self.log_save_path_edit.setStyleSheet(
            dialog_line_edit_style(size=12, min_height=24, padding="3px 6px")
        )
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

        color_info = QLabel(log_color_info_text())
        color_info.setStyleSheet(log_color_info_style())
        color_info.setWordWrap(True)
        layout.addWidget(color_info)

        layout.addStretch()
        return page

    # ---- tab: Display ----

    def _build_tab_display(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        layout.addWidget(self._section_title("Font"))

        font_row = QHBoxLayout()
        font_row.setSpacing(8)
        font_row.addWidget(QLabel("Font family"))
        self.display_font_combo = SerialDarkComboBox()
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
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

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

    # ---- tab: About ----

    def _build_tab_about(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(transparent_scroll_area_style() + SERIAL_SCROLLBAR_STYLE)

        content = QWidget()
        content.setObjectName("aboutPage")
        content.setStyleSheet("""
            QWidget#aboutPage QLabel#aboutHeroTitle {
                color: #1d1d1f;
                font-size: 19px;
                font-weight: 800;
            }
            QWidget#aboutPage QLabel#aboutHeroSub {
                color: #6e6e73;
                font-size: 12px;
            }
            QWidget#aboutPage QLabel#aboutCardTitle {
                color: #4f5b6b;
                font-size: 12px;
                font-weight: 800;
            }
            QWidget#aboutPage QLabel#aboutKey {
                color: #7a8290;
                font-size: 11px;
            }
            QWidget#aboutPage QLabel#aboutValue {
                color: #263245;
                font-size: 12px;
                font-weight: 600;
            }
            QWidget#aboutPage QLabel#aboutResetHint {
                color: #5d6675;
                font-size: 12px;
                line-height: 1.35;
            }
        """)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        about_info = {}
        parent = self.parent()
        if parent is not None and hasattr(parent, "_sc_about_info"):
            about_info = parent._sc_about_info()

        hero = QFrame()
        hero.setObjectName("scSectionCard")
        hero.setStyleSheet(section_card_style())
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(16, 14, 16, 14)
        hero_layout.setSpacing(5)

        title = QLabel(about_info.get("Application", "KK Serial Console"))
        title.setObjectName("aboutHeroTitle")
        hero_layout.addWidget(title)

        subtitle = QLabel(
            f"Version {about_info.get('Version', '1.0.0')}  |  "
            f"Author: {about_info.get('Author', 'KK_Lab Team')}"
        )
        subtitle.setObjectName("aboutHeroSub")
        hero_layout.addWidget(subtitle)
        layout.addWidget(hero)

        info_card = QFrame()
        info_card.setObjectName("scSectionCard")
        info_card.setStyleSheet(section_card_style())
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(14, 12, 14, 12)
        info_layout.setSpacing(9)

        info_title = QLabel("Software Information")
        info_title.setObjectName("aboutCardTitle")
        info_layout.addWidget(info_title)

        info_grid = QGridLayout()
        info_grid.setHorizontalSpacing(14)
        info_grid.setVerticalSpacing(7)
        display_items = [
            ("Config schema", about_info.get("Config schema", "")),
            ("Quick Commands", about_info.get("Quick Commands", "0")),
            ("Runtime mode", about_info.get("Runtime mode", "")),
            ("Primary screen", about_info.get("Primary screen", "")),
        ]
        for row, (key, value) in enumerate(display_items):
            key_label = QLabel(key)
            key_label.setObjectName("aboutKey")
            info_grid.addWidget(key_label, row, 0)

            value_label = QLabel(str(value))
            value_label.setObjectName("aboutValue")
            value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            info_grid.addWidget(value_label, row, 1)
        info_grid.setColumnStretch(1, 1)
        info_layout.addLayout(info_grid)
        layout.addWidget(info_card)

        config_card = QFrame()
        config_card.setObjectName("scSectionCard")
        config_card.setStyleSheet(section_card_style())
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(14, 12, 14, 12)
        config_layout.setSpacing(9)

        config_title = QLabel("User Configuration")
        config_title.setObjectName("aboutCardTitle")
        config_layout.addWidget(config_title)

        for key, value in (
            ("JSON file", about_info.get("Config file", "")),
            ("Directory", about_info.get("Config directory", "")),
        ):
            key_label = QLabel(key)
            key_label.setObjectName("aboutKey")
            config_layout.addWidget(key_label)

            path_edit = QLineEdit(str(value))
            path_edit.setReadOnly(True)
            path_edit.setCursorPosition(0)
            path_edit.setStyleSheet(dialog_line_edit_style(size=11, min_height=22, padding="3px 7px"))
            path_edit.setFixedHeight(28)
            config_layout.addWidget(path_edit)
            config_layout.addSpacing(4)

        reset_info = QLabel(
            "Reset restores Serial, RX/TX, display, history, and window settings to defaults. "
            "Quick Commands are kept unchanged."
        )
        reset_info.setObjectName("aboutResetHint")
        reset_info.setWordWrap(True)
        config_layout.addWidget(reset_info)

        reset_btn = QPushButton("Reset User JSON...")
        reset_btn.setObjectName("dlgCancelBtn")
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setAutoDefault(False)
        reset_btn.setDefault(False)
        reset_btn.clicked.connect(self._on_reset_user_json_clicked)

        reset_row = QHBoxLayout()
        reset_row.addWidget(reset_btn)
        reset_row.addStretch()
        config_layout.addLayout(reset_row)

        layout.addWidget(config_card)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ---- helpers ----

    def _on_reset_user_json_clicked(self):
        parent = self.parent()
        if parent is not None and hasattr(parent, "_sc_reset_user_config_keep_quick_commands"):
            if parent._sc_reset_user_config_keep_quick_commands(self):
                self.reject()

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


class _NtpSyncWorker(QObject):
    synced = Signal(float, float)
    failed = Signal(str)
    finished = Signal()

    _NTP_SERVERS = (
        "pool.ntp.org",
        "time.windows.com",
        "time.google.com",
        "ntp.aliyun.com",
        "cn.pool.ntp.org",
    )
    _NTP_PORT = 123
    _NTP_DELTA = 2208988800.0
    _RESYNC_INTERVAL_S = 300.0
    _SOCKET_TIMEOUT_S = 3.0
    _RETRY_SLEEP_MS = 5000

    def __init__(self):
        super().__init__()
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        import socket
        import struct

        while self._running:
            offset = None
            rtt = None
            last_error = ""
            for server in self._NTP_SERVERS:
                if not self._running:
                    break
                try:
                    packet = bytearray(48)
                    packet[0] = 0x1B
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.settimeout(self._SOCKET_TIMEOUT_S)
                    try:
                        t0 = time.time()
                        sock.sendto(bytes(packet), (server, self._NTP_PORT))
                        data, _ = sock.recvfrom(48)
                        t3 = time.time()
                    finally:
                        sock.close()
                    if len(data) < 48:
                        last_error = f"{server}: short response"
                        continue
                    recv_int, recv_frac = struct.unpack("!II", data[32:40])
                    tx_int, tx_frac = struct.unpack("!II", data[40:48])
                    t1 = (recv_int + recv_frac / 2 ** 32) - self._NTP_DELTA
                    t2 = (tx_int + tx_frac / 2 ** 32) - self._NTP_DELTA
                    rtt = (t3 - t0) - (t2 - t1)
                    offset = ((t1 - t0) + (t2 - t3)) / 2.0
                    break
                except Exception as e:
                    last_error = f"{server}: {e}"
                    continue

            if not self._running:
                break

            if offset is not None:
                self.synced.emit(offset, rtt or 0.0)
                slept = 0
                while self._running and slept < self._RESYNC_INTERVAL_S * 1000:
                    QThread.msleep(200)
                    slept += 200
            else:
                self.failed.emit(last_error or "All NTP servers unreachable")
                slept = 0
                while self._running and slept < self._RETRY_SLEEP_MS:
                    QThread.msleep(200)
                    slept += 200

        self.finished.emit()


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
            self._sc_append_system("[INFO] KK Serials initialized", force_primary=True)

        def append_log(self, msg):
            self._sc_append_system(msg, force_primary=True)

        def closeEvent(self, event):
            try:
                self._sc_save_persisted_state()
            except Exception:
                pass
            self.close_serial()
            if hasattr(self, '_sc_independent_windows'):
                for win in list(self._sc_independent_windows):
                    win.close()
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
    w4._sc_apply_window_geometry()
    if getattr(w4, "_sc_restore_maximized", False):
        w4.showMaximized()
    else:
        w4.show()

    sys.exit(app.exec())
