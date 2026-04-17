import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject, QRectF
from PySide6.QtGui import QIcon, QPainter
from PySide6.QtSvg import QSvgRenderer
import pyvisa

from instruments.power.keysight.n6705c import N6705C
from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.button import SpinningSearchButton, update_connect_button_state
from debug_config import DEBUG_MOCK
from instruments.mock.mock_instruments import MockN6705C


_ICONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "resources", "icons"
)
_SEARCH_ICON_PATH = os.path.join(_ICONS_DIR, "search.svg")
_LINK_ICON_PATH = os.path.join(_ICONS_DIR, "link.svg")
_UNLINK_ICON_PATH = os.path.join(_ICONS_DIR, "unlink.svg")

DEFAULT_VISA_RESOURCE = "TCPIP0::K-N6705C-06098.local::hislip0::INSTR"

N6705C_BTN_HEIGHT = 24
N6705C_BTN_ICON_SIZE = 14
N6705C_BTN_RADIUS = 6


def _n6705c_search_style(h=N6705C_BTN_HEIGHT, r=N6705C_BTN_RADIUS):
    inner = max(h - 2, 0)
    return f"""
        QPushButton {{
            background-color: #13254b;
            border: 1px solid #22376A;
            border-radius: {r}px;
            color: #dce7ff;
            font-weight: 600;
            min-height: {inner}px;
            max-height: {inner}px;
        }}
        QPushButton:hover {{
            background-color: #1C2D55;
            border: 1px solid #3A5A9F;
        }}
        QPushButton:pressed {{
            background-color: #102040;
        }}
        QPushButton:disabled {{
            background-color: #0b1430;
            color: #5c7096;
            border: 1px solid #1a2850;
        }}
    """


def _n6705c_connect_style(h=N6705C_BTN_HEIGHT, r=N6705C_BTN_RADIUS):
    inner = max(h - 2, 0)
    return f"""
        QPushButton {{
            background-color: #053b38;
            border: 1px solid #08c9a5;
            border-radius: {r}px;
            color: #10e7bc;
            font-weight: 700;
            min-height: {inner}px;
            max-height: {inner}px;
        }}
        QPushButton:hover {{
            background-color: #064744;
            border: 1px solid #19f0c5;
            color: #43f3d0;
        }}
        QPushButton:pressed {{
            background-color: #042f2d;
        }}
        QPushButton:disabled {{
            background-color: #0D1734;
            color: #3a4a6a;
            border: 1px solid #18264A;
        }}
    """


def _n6705c_disconnect_style(h=N6705C_BTN_HEIGHT, r=N6705C_BTN_RADIUS):
    inner = max(h - 2, 0)
    return f"""
        QPushButton {{
            background-color: #3a0828;
            border: 1px solid #d61b67;
            border-radius: {r}px;
            color: #ffb7d3;
            font-weight: 700;
            min-height: {inner}px;
            max-height: {inner}px;
        }}
        QPushButton:hover {{
            background-color: #4a0b31;
            border: 1px solid #f0287b;
            color: #ffd0e2;
        }}
        QPushButton:pressed {{
            background-color: #330722;
        }}
        QPushButton:disabled {{
            background-color: #0D1734;
            color: #3a4a6a;
            border: 1px solid #18264A;
        }}
    """


class _N6705CSearchButton(QPushButton):
    def __init__(self, parent=None, icon_size=N6705C_BTN_ICON_SIZE,
                 btn_height=N6705C_BTN_HEIGHT, btn_radius=N6705C_BTN_RADIUS):
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
        self.setStyleSheet(_n6705c_search_style(h=btn_height, r=btn_radius))

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


def _update_n6705c_btn_state(btn, connected,
                             h=N6705C_BTN_HEIGHT, r=N6705C_BTN_RADIUS,
                             icon_size=N6705C_BTN_ICON_SIZE):
    update_connect_button_state(btn, connected)


class _SearchN6705CWorker(QObject):
    finished = Signal(list)
    error = Signal(str)

    def run(self):
        rm = None
        try:
            rm = pyvisa.ResourceManager()
            resources = list(rm.list_resources()) or []
            n6705c_devices = []
            for dev in resources:
                instr = None
                try:
                    instr = rm.open_resource(dev, timeout=1000)
                    idn = instr.query('*IDN?').strip()
                    if "N6705C" in idn:
                        n6705c_devices.append(dev)
                except Exception:
                    pass
                finally:
                    if instr is not None:
                        try:
                            instr.close()
                        except Exception:
                            pass
            self.finished.emit(n6705c_devices)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            if rm is not None:
                try:
                    rm.close()
                except Exception:
                    pass


_INLINE_ROW_TAG_COLORS = {
    "A": "#00f5c4",
    "B": "#f2994a",
}


def build_n6705c_inline_row(label, parent=None,
                           btn_height=N6705C_BTN_HEIGHT,
                           btn_radius=N6705C_BTN_RADIUS,
                           btn_icon_size=N6705C_BTN_ICON_SIZE,
                           row_height=None,
                           default_resource=None):
    tag_color = _INLINE_ROW_TAG_COLORS.get(label, "#00f5c4")
    h = row_height if row_height is not None else btn_height

    row = QHBoxLayout()
    row.setSpacing(10)
    row.setContentsMargins(0, 0, 0, 0)
    row.setAlignment(Qt.AlignVCenter)

    tag = QLabel(f"  {label}  ")
    tag.setAlignment(Qt.AlignCenter)
    tag.setStyleSheet(
        f"color: {tag_color}; font-weight: 900; font-size: 14px; min-width: 24px;"
        " background: transparent; border: none;"
    )
    row.addWidget(tag, 0, Qt.AlignVCenter)

    status_label = QLabel("● Disconnected")
    status_label.setFixedWidth(120)
    status_label.setStyleSheet("color: #8ea6cf; font-weight: bold; background: transparent; border: none;")
    row.addWidget(status_label, 0, Qt.AlignVCenter)

    visa_combo = DarkComboBox(bg="#091426", border="#17345f")
    visa_combo.setMinimumWidth(300)
    visa_combo.setSizeAdjustPolicy(DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    visa_combo.setMinimumContentsLength(10)
    visa_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    visa_combo.setFixedHeight(h)
    visa_combo.addItem(default_resource if default_resource else DEFAULT_VISA_RESOURCE)
    row.addWidget(visa_combo, 1, Qt.AlignVCenter)

    search_btn = SpinningSearchButton(parent=parent)
    search_btn.setFixedHeight(h)
    row.addWidget(search_btn, 0, Qt.AlignVCenter)

    connect_btn = QPushButton()
    connect_btn.setFixedHeight(h)
    connect_btn.setFixedWidth(110)
    update_connect_button_state(connect_btn, connected=False)
    row.addWidget(connect_btn, 0, Qt.AlignVCenter)

    return row, {
        "tag": tag,
        "status": status_label,
        "combo": visa_combo,
        "search_btn": search_btn,
        "connect_btn": connect_btn,
    }


class N6705CConnectionMixin:
    connection_status_changed = Signal(bool)

    def init_n6705c_connection(self, n6705c_top=None):
        self._n6705c_top = n6705c_top
        self.rm = None
        self.n6705c = None
        self.is_connected = False
        self.available_devices = []
        self._n6705c_search_thread = None
        self._n6705c_search_worker = None
        self._n6705c_btn_height = N6705C_BTN_HEIGHT
        self._n6705c_btn_radius = N6705C_BTN_RADIUS
        self._n6705c_btn_icon_size = N6705C_BTN_ICON_SIZE

        if self._n6705c_top is not None and hasattr(self._n6705c_top, 'connection_changed'):
            self._n6705c_top.connection_changed.connect(self.sync_n6705c_from_top)

    def build_n6705c_connection_widgets(self, layout,
                                        btn_height=N6705C_BTN_HEIGHT,
                                        btn_radius=N6705C_BTN_RADIUS,
                                        btn_icon_size=N6705C_BTN_ICON_SIZE):
        self._n6705c_btn_height = btn_height
        self._n6705c_btn_radius = btn_radius
        self._n6705c_btn_icon_size = btn_icon_size

        self.system_status_label = QLabel("● Ready")
        self.system_status_label.setObjectName("statusOk")
        layout.addWidget(self.system_status_label)

        self.visa_resource_combo = DarkComboBox()
        self.visa_resource_combo.setSizeAdjustPolicy(
            DarkComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.visa_resource_combo.setMinimumContentsLength(10)
        self.visa_resource_combo.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        self.visa_resource_combo.addItem(DEFAULT_VISA_RESOURCE)
        layout.addWidget(self.visa_resource_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.search_btn = _N6705CSearchButton(
            icon_size=btn_icon_size,
            btn_height=btn_height,
            btn_radius=btn_radius,
        )

        self.connect_btn = QPushButton()
        _update_n6705c_btn_state(
            self.connect_btn, connected=False,
            h=btn_height, r=btn_radius, icon_size=btn_icon_size,
        )

        btn_row.addWidget(self.search_btn)
        btn_row.addWidget(self.connect_btn)
        layout.addLayout(btn_row)

    def bind_n6705c_signals(self):
        self.search_btn.clicked.connect(self._on_n6705c_search)
        self.connect_btn.clicked.connect(self._on_n6705c_connect_or_disconnect)

    def _update_n6705c_connect_button_state(self, connected: bool):
        self.is_connected = connected
        _update_n6705c_btn_state(
            self.connect_btn, connected,
            h=self._n6705c_btn_height,
            r=self._n6705c_btn_radius,
            icon_size=self._n6705c_btn_icon_size,
        )

    def sync_n6705c_from_top(self):
        if not self._n6705c_top:
            return
        if self._n6705c_top.is_connected_a and self._n6705c_top.n6705c_a:
            self.n6705c = self._n6705c_top.n6705c_a
            self._update_n6705c_connect_button_state(True)
            self.search_btn.setEnabled(False)
            if self._n6705c_top.visa_resource_a:
                self.visa_resource_combo.clear()
                self.visa_resource_combo.addItem(self._n6705c_top.visa_resource_a)
                pretty_name = self._n6705c_top.visa_resource_a
                try:
                    pretty_name = self._n6705c_top.visa_resource_a.split("::")[1]
                except Exception:
                    pass
                self.set_system_status(f"● Connected to: {pretty_name}")
        else:
            self.n6705c = None
            self._update_n6705c_connect_button_state(False)
            self.search_btn.setEnabled(True)
            self.visa_resource_combo.setEnabled(True)
            self.set_system_status("● Ready")

    def set_system_status(self, status, is_error=False):
        self.system_status_label.setText(status)
        if is_error:
            self.system_status_label.setObjectName("statusErr")
        elif any(kw in status for kw in ["Running", "Searching", "Connecting", "Disconnecting"]):
            self.system_status_label.setObjectName("statusWarn")
        else:
            self.system_status_label.setObjectName("statusOk")
        self.system_status_label.style().unpolish(self.system_status_label)
        self.system_status_label.style().polish(self.system_status_label)
        self.system_status_label.update()

    def _on_n6705c_search(self):
        if self._n6705c_top and self._n6705c_top.is_connected_a:
            return
        if DEBUG_MOCK:
            self.visa_resource_combo.clear()
            self.visa_resource_combo.addItem("DEBUG::MOCK::N6705C")
            self.set_system_status("● Mock device ready")
            if hasattr(self, 'append_log'):
                self.append_log("[DEBUG] Mock device loaded, skip real VISA scan.")
            return
        self.set_system_status("● Searching")
        if hasattr(self, 'append_log'):
            self.append_log("[SYSTEM] Scanning VISA resources...")
        self.search_btn.setEnabled(False)
        self.connect_btn.setEnabled(False)

        if self._n6705c_search_thread is not None and self._n6705c_search_thread.isRunning():
            return

        worker = _SearchN6705CWorker()
        thread = QThread()
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_n6705c_search_done)
        worker.error.connect(self._on_n6705c_search_error)
        worker.finished.connect(thread.quit)
        worker.error.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._on_n6705c_search_thread_cleanup())

        self._n6705c_search_thread = thread
        self._n6705c_search_worker = worker
        thread.start()

    def _on_n6705c_search_thread_cleanup(self):
        self._n6705c_search_thread = None
        self._n6705c_search_worker = None

    def _on_n6705c_search_done(self, n6705c_devices):
        self.visa_resource_combo.setEnabled(True)
        self.visa_resource_combo.clear()

        if n6705c_devices:
            for dev in n6705c_devices:
                self.visa_resource_combo.addItem(dev)
            count = len(n6705c_devices)
            self.set_system_status(f"● Found {count} device(s)")
            if hasattr(self, 'append_log'):
                self.append_log(f"[SYSTEM] Found {count} compatible N6705C device(s).")
            if DEFAULT_VISA_RESOURCE in n6705c_devices:
                self.visa_resource_combo.setCurrentText(DEFAULT_VISA_RESOURCE)
            else:
                self.visa_resource_combo.setCurrentIndex(0)
        else:
            self.visa_resource_combo.addItem("No N6705C device found")
            self.visa_resource_combo.setEnabled(False)
            self.set_system_status("● No device found", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log("[SYSTEM] No compatible N6705C instrument found.")

        self.search_btn.setEnabled(True)
        self.connect_btn.setEnabled(True)

    def _on_n6705c_search_error(self, err):
        self.set_system_status("● Search failed", is_error=True)
        if hasattr(self, 'append_log'):
            self.append_log(f"[ERROR] Search failed: {err}")
        self.search_btn.setEnabled(True)
        self.connect_btn.setEnabled(True)

    def _on_n6705c_connect_or_disconnect(self):
        if self.is_connected:
            self._on_n6705c_disconnect()
        else:
            self._on_n6705c_connect()

    def _on_n6705c_connect(self):
        if DEBUG_MOCK:
            self.n6705c = MockN6705C()
            self._update_n6705c_connect_button_state(True)
            self.set_system_status("● Connected to: Mock N6705C (DEBUG)")
            self.search_btn.setEnabled(False)
            if hasattr(self, 'append_log'):
                self.append_log("[DEBUG] Mock N6705C connected.")
            device_address = self.visa_resource_combo.currentText()
            if self._n6705c_top:
                self._n6705c_top.connect_a(device_address, self.n6705c)
            self.connection_status_changed.emit(True)
            return

        self.set_system_status("● Connecting")
        if hasattr(self, 'append_log'):
            self.append_log("[SYSTEM] Attempting instrument connection...")
        self.connect_btn.setEnabled(False)

        try:
            device_address = self.visa_resource_combo.currentText()
            self.n6705c = N6705C(device_address)

            idn = self.n6705c.instr.query("*IDN?")
            if "N6705C" in idn:
                self._update_n6705c_connect_button_state(True)
                self.search_btn.setEnabled(False)

                pretty_name = device_address
                try:
                    pretty_name = device_address.split("::")[1]
                except Exception:
                    pass

                self.set_system_status(f"● Connected to: {pretty_name}")
                if hasattr(self, 'append_log'):
                    self.append_log("[SYSTEM] N6705C connected successfully.")
                    self.append_log(f"[IDN] {idn.strip()}")

                if self._n6705c_top:
                    self._n6705c_top.connect_a(device_address, self.n6705c)

                self.connection_status_changed.emit(True)
            else:
                self.set_system_status("● Device mismatch", is_error=True)
                if hasattr(self, 'append_log'):
                    self.append_log("[ERROR] Connected device is not N6705C.")
        except Exception as e:
            self.set_system_status("● Connection failed", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[ERROR] Connection failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def _on_n6705c_disconnect(self):
        self.set_system_status("● Disconnecting")
        if hasattr(self, 'append_log'):
            self.append_log("[SYSTEM] Disconnecting instrument...")
        self.connect_btn.setEnabled(False)

        try:
            if self._n6705c_top:
                self._n6705c_top.disconnect_a()
                self.n6705c = None
            else:
                if self.n6705c is not None:
                    if hasattr(self.n6705c, 'instr') and self.n6705c.instr:
                        self.n6705c.instr.close()
                    if hasattr(self.n6705c, 'rm') and self.n6705c.rm:
                        self.n6705c.rm.close()
                self.n6705c = None

            self._update_n6705c_connect_button_state(False)
            self.set_system_status("● Ready")
            self.search_btn.setEnabled(True)
            if hasattr(self, 'append_log'):
                self.append_log("[SYSTEM] Instrument disconnected.")
            self.connection_status_changed.emit(False)
        except Exception as e:
            self.set_system_status("● Disconnect failed", is_error=True)
            if hasattr(self, 'append_log'):
                self.append_log(f"[ERROR] Disconnect failed: {str(e)}")
        finally:
            self.connect_btn.setEnabled(True)

    def get_n6705c_instance(self):
        return self.n6705c

    def is_n6705c_connected(self):
        return self.is_connected
