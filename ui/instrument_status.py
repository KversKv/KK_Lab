from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Qt

from ui.widgets.toast_notification import ToastNotification
from log_config import get_logger

logger = get_logger(__name__)


class InstrumentStatusPanel:
    def __init__(self, host):
        self._host = host
        self._toast = ToastNotification()
        self._prev_instrument_keys: set = set()
        self.instrument_status_items: dict = {}

    def create_bottom_widget(self):
        bottom_widget = QWidget()
        bottom_widget.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(12)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("""
            QFrame {
                background-color: #1a2238;
                border: none;
            }
        """)
        bottom_layout.addWidget(divider)

        self.help_btn = QPushButton("\uff1f Help")
        self.help_btn.setCursor(Qt.PointingHandCursor)
        self.help_btn.setStyleSheet("""
            QPushButton {
                min-height: 42px;
                background-color: #4f3df0;
                color: white;
                border: none;
                border-radius: 10px;
                font-weight: 600;
                text-align: center;
                padding: 0 12px;
            }
            QPushButton:hover {
                background-color: #5b49ff;
            }
            QPushButton:pressed {
                background-color: #4534dd;
            }
        """)
        bottom_layout.addWidget(self.help_btn)

        self.instrument_status_container = QWidget()
        self.instrument_status_container.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        self.instrument_status_layout = QVBoxLayout(self.instrument_status_container)
        self.instrument_status_layout.setContentsMargins(0, 0, 0, 0)
        self.instrument_status_layout.setSpacing(4)
        bottom_layout.addWidget(self.instrument_status_container)

        return bottom_widget

    def _add_instrument_status(self, key: str, text: str):
        if key in self.instrument_status_items:
            return
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: transparent;
                border: none;
            }
        """)
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        dot = QLabel("\u25cf")
        dot.setStyleSheet("""
            QLabel {
                color: #00d38a;
                font-size: 12px;
                border: none;
                background: transparent;
            }
        """)
        dot.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        if "to:" in text:
            head, tail = text.split("to:", 1)
            display_text = f"{head}to:\n    {tail.strip()}"
        else:
            display_text = text

        label = QLabel(display_text)
        label.setWordWrap(True)
        label.setStyleSheet("""
            QLabel {
                color: #9fd3c7;
                font-size: 11px;
                border: none;
                background: transparent;
            }
        """)

        layout.addWidget(dot, 0, Qt.AlignTop)
        layout.addWidget(label, 1)

        self.instrument_status_layout.addWidget(widget)
        self.instrument_status_items[key] = widget

    def _remove_instrument_status(self, key: str):
        widget = self.instrument_status_items.pop(key, None)
        if widget is not None:
            self.instrument_status_layout.removeWidget(widget)
            widget.deleteLater()

    def update_instrument_status(self):
        n6705c_top = self._host.n6705c_top
        mso64b_top = self._host.mso64b_top

        if n6705c_top.is_connected_a:
            name = f"N6705C-A Connected to: {n6705c_top.serial_a}" if n6705c_top.serial_a else "N6705C-A Connected"
            self._remove_instrument_status("n6705c_a")
            self._add_instrument_status("n6705c_a", name)
        else:
            self._remove_instrument_status("n6705c_a")

        if n6705c_top.is_connected_b:
            name = f"N6705C-B Connected to: {n6705c_top.serial_b}" if n6705c_top.serial_b else "N6705C-B Connected"
            self._remove_instrument_status("n6705c_b")
            self._add_instrument_status("n6705c_b", name)
        else:
            self._remove_instrument_status("n6705c_b")

        scope_shown = False
        oscilloscope_ui = self._host.oscilloscope_ui
        if oscilloscope_ui is not None and oscilloscope_ui.controller.is_connected and oscilloscope_ui.controller.instrument_info:
            parts = [p.strip() for p in oscilloscope_ui.controller.instrument_info.split(",")]
            if len(parts) >= 3:
                name = f"{parts[1]}  {parts[2]}"
            elif len(parts) >= 2:
                name = parts[1]
            else:
                name = oscilloscope_ui.controller.instrument_info
            self._remove_instrument_status("oscilloscope")
            self._add_instrument_status("oscilloscope", name)
            scope_shown = True
        elif mso64b_top and mso64b_top.is_connected and mso64b_top.mso64b:
            scope_type = getattr(mso64b_top, 'scope_type', '') or 'Oscilloscope'
            try:
                idn = mso64b_top.mso64b.identify_instrument()
                parts = [p.strip() for p in idn.split(",")]
                if len(parts) >= 3:
                    name = f"{parts[1]}  {parts[2]}"
                elif len(parts) >= 2:
                    name = parts[1]
                else:
                    name = idn
            except Exception:
                name = f"{scope_type} Connected"
            self._remove_instrument_status("oscilloscope")
            self._add_instrument_status("oscilloscope", name)
            scope_shown = True

        if not scope_shown:
            self._remove_instrument_status("oscilloscope")

        vt6002_chamber_ui = self._host.vt6002_chamber_ui
        if vt6002_chamber_ui is not None and vt6002_chamber_ui.vt6002 is not None:
            self._remove_instrument_status("vt6002")
            self._add_instrument_status("vt6002", "VT6002 Chamber Connected")
        else:
            self._remove_instrument_status("vt6002")

        current_keys = set(self.instrument_status_items.keys())
        newly_connected = current_keys - self._prev_instrument_keys
        newly_disconnected = self._prev_instrument_keys - current_keys

        for key in newly_connected:
            display_name = key.replace("_", " ").replace("n6705c", "N6705C").title()
            self._toast.show_toast(f"{display_name} Connected", ToastNotification.TYPE_SUCCESS, self._host)
        for key in newly_disconnected:
            display_name = key.replace("_", " ").replace("n6705c", "N6705C").title()
            self._toast.show_toast(f"{display_name} Disconnected", ToastNotification.TYPE_ERROR, self._host)

        self._prev_instrument_keys = current_keys
