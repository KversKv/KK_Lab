from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)
from PySide6.QtCore import Qt

from ui.widgets.toast_notification import ToastNotification
from log_config import get_logger

logger = get_logger(__name__)

_DISPLAY_NAME_MAP = {
    "n6705c": "N6705C",
    "mso64b": "MSO64B",
    "dsox4034a": "DSOX4034A",
    "vt6002": "VT6002",
    "mt3065": "MT3065",
    "keysight53230a": "53230A",
    "serial_port": "Serial",
    "bes_usb_i2c": "USB-I2C",
}


class InstrumentStatusPanel:
    def __init__(self, host):
        self._host = host
        self._toast = ToastNotification()
        self._prev_instrument_keys: set = set()
        self.instrument_status_items: dict = {}
        self._suppressed = False

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

    def _add_instrument_status(self, key: str, text: str, dot_color: str = "#00d38a"):
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
        dot.setStyleSheet(f"""
            QLabel {{
                color: {dot_color};
                font-size: 12px;
                border: none;
                background: transparent;
            }}
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

    def suppress_toasts(self):
        self._suppressed = True
        self._toast.force_close()

    def _format_snapshot_display(self, snapshot) -> str:
        type_name = _DISPLAY_NAME_MAP.get(snapshot.instrument_type, snapshot.instrument_type)
        slot = snapshot.slot
        if slot and slot not in ("default",):
            label = f"{type_name}-{slot.upper()}"
        else:
            label = type_name

        status_suffix = ""
        if snapshot.disconnecting:
            status_suffix = " [Disconnecting...]"
        elif snapshot.busy:
            owner_part = f" by {snapshot.busy_owner}" if snapshot.busy_owner else ""
            status_suffix = f" [Busy{owner_part}]"

        if snapshot.model and snapshot.serial:
            return f"{label} Connected to: {snapshot.model} {snapshot.serial}{status_suffix}"
        elif snapshot.serial:
            return f"{label} Connected to: {snapshot.serial}{status_suffix}"
        elif snapshot.model:
            return f"{label} Connected ({snapshot.model}){status_suffix}"
        return f"{label} Connected{status_suffix}"

    def update_instrument_status(self):
        manager = getattr(self._host, "instrument_manager", None)
        if manager is None:
            return

        snapshots = manager.sessions()
        active_keys: set = set()

        for snap in snapshots:
            if not snap.connected and not snap.disconnecting:
                continue
            key = snap.session_id
            active_keys.add(key)
            display_text = self._format_snapshot_display(snap)
            if snap.disconnecting:
                dot_color = "#ff9800"
            elif snap.busy:
                dot_color = "#ffeb3b"
            else:
                dot_color = "#00d38a"
            self._remove_instrument_status(key)
            self._add_instrument_status(key, display_text, dot_color=dot_color)

        stale_keys = set(self.instrument_status_items.keys()) - active_keys
        for key in stale_keys:
            self._remove_instrument_status(key)

        current_keys = set(self.instrument_status_items.keys())
        newly_connected = current_keys - self._prev_instrument_keys
        newly_disconnected = self._prev_instrument_keys - current_keys

        if not self._suppressed:
            for key in newly_connected:
                parts = key.split(":")
                type_name = _DISPLAY_NAME_MAP.get(parts[0], parts[0]) if parts else key
                slot_part = f"-{parts[1].upper()}" if len(parts) > 1 and parts[1] not in ("default",) else ""
                self._toast.show_toast(
                    f"{type_name}{slot_part} Connected",
                    ToastNotification.TYPE_SUCCESS, self._host,
                )
            for key in newly_disconnected:
                parts = key.split(":")
                type_name = _DISPLAY_NAME_MAP.get(parts[0], parts[0]) if parts else key
                slot_part = f"-{parts[1].upper()}" if len(parts) > 1 and parts[1] not in ("default",) else ""
                self._toast.show_toast(
                    f"{type_name}{slot_part} Disconnected",
                    ToastNotification.TYPE_ERROR, self._host,
                )

        self._prev_instrument_keys = current_keys
