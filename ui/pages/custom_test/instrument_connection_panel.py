"""Custom Test instrument connection panel."""

from __future__ import annotations

from typing import Iterable

from PySide6.QtWidgets import (
    QFrame,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.instruments import InstrumentSpec
from log_config import get_logger
from ui.widgets.button import SpinningSearchButton
from ui.widgets.dark_combobox import DarkComboBox

logger = get_logger(__name__)


class InstrumentConnectionPanel(QWidget):
    """Left-side connection area used by Custom Test."""

    def __init__(self, page: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._page = page
        self._pending_instr_meta: dict | None = None
        self._n6705c_widgets_built = False
        self._chamber_widgets_built = False
        self._uart_widgets_built = False
        self._mcu_io_widgets_built = False
        self._running = False

        self.setStyleSheet("""
            QWidget { background: transparent; border: none; }
            QLabel#fieldLabel {
                color: #8eb0e3; font-size: 11px;
                background: transparent; border: none;
            }
            QLabel#placeholderText {
                color: #3f5070; font-size: 11px;
                background: transparent; border: none;
            }
            QLabel#statusOk {
                color: #15d1a3; font-weight: 600; font-size: 11px;
                background: transparent; border: none;
            }
            QLabel#statusWarn {
                color: #ffb84d; font-weight: 600; font-size: 11px;
                background: transparent; border: none;
            }
            QLabel#statusErr {
                color: #ff5e7a; font-weight: 600; font-size: 11px;
                background: transparent; border: none;
            }
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._show_placeholder()

    def refresh(self, used_ids: Iterable[str]) -> None:
        self._clear_layout()
        used = set(used_ids)
        self._set_built_flags(False, False, False, False)

        if not used:
            self._show_placeholder()
            self._apply_running_state()
            return

        if "n6705c" in used:
            self._add_label("N6705C Power Analyzer")
            title_row = QHBoxLayout()
            title_row.setSpacing(8)
            self._page.build_n6705c_connection_widgets(self._layout, title_row=title_row)
            self._page.bind_n6705c_signals()
            self._set_n6705c_built(True)
            if getattr(self._page, "_n6705c_top_ref", None):
                self.sync_n6705c_from_top()

        if "chamber" in used:
            self._add_label("Chamber")
            self._page.build_chamber_connection_widgets(self._layout)
            self._page.bind_chamber_signals()
            self._set_chamber_built(True)
            chamber_ui = getattr(self._page, "_chamber_ui_ref", None)
            if chamber_ui and getattr(chamber_ui, "chamber", None):
                self.on_chamber_external_changed()

        if "scope" in used:
            self._add_label("Oscilloscope")
            scope_top = getattr(self._page, "_mso64b_top_ref", None)
            scope_status = QLabel("● Synced from main" if scope_top else "● Not available")
            scope_status.setObjectName("statusOk" if scope_top else "statusErr")
            self._layout.addWidget(scope_status)

        if "rf_analyzer" in used:
            self._add_label("CMW270 RF Analyzer")
            status = QLabel("● Not implemented")
            status.setObjectName("statusWarn")
            self._layout.addWidget(status)

        if "i2c" in used:
            self._add_label("REG Controller (I2C)")
            status = QLabel("● Auto-connect on run")
            status.setObjectName("statusOk")
            self._layout.addWidget(status)

        if "mcu_io" in used:
            self._add_label("MCU IO")
            self._build_mcu_io_connection_widgets()
            self._set_mcu_io_built(True)
            self.sync_mcu_io_from_manager()

        if "uart" in used:
            self._add_label("UART (Serial)")
            self._page.build_serial_connection_widgets(self._layout)
            self._page.bind_serial_signals()
            self._set_uart_built(True)
            if getattr(self._page, "_serial_connected", False):
                self._page._update_serial_connect_ui(True)

        self.apply_instrument_meta()
        self._apply_running_state()

    def set_running_state(self, running: bool) -> None:
        self._running = running
        self._apply_running_state()

    def _apply_running_state(self) -> None:
        enabled = not self._running
        for widget in self.findChildren((QPushButton, QComboBox, QLineEdit)):
            widget.setEnabled(enabled)

    def collect_meta(self) -> dict:
        meta = {}
        page = self._page
        if self._n6705c_widgets_built and hasattr(page, "visa_resource_combo"):
            meta["n6705c"] = {"visa": page.visa_resource_combo.currentText()}
        if self._chamber_widgets_built and hasattr(page, "chamber_port_combo"):
            meta["chamber"] = {
                "type": page.chamber_type_combo.currentData() if hasattr(page, "chamber_type_combo") else "vt6002",
                "port": page.chamber_port_combo.currentText(),
            }
        if self._uart_widgets_built and hasattr(page, "_sc_port_combo"):
            meta["uart"] = {
                "port": page._sc_port_combo.currentText(),
                "baud": page._sc_baud_combo.currentText(),
            }
        if self._mcu_io_widgets_built and hasattr(page, "mcu_io_port_combo"):
            meta["mcu_io"] = {"port": self._mcu_io_selected_resource()}
        return meta

    def on_metadata_loaded(self, meta: dict) -> None:
        self._pending_instr_meta = meta
        self.apply_instrument_meta()

    def apply_instrument_meta(self) -> None:
        meta = self._pending_instr_meta
        if not meta:
            return
        page = self._page
        if "n6705c" in meta and self._n6705c_widgets_built:
            visa = meta["n6705c"].get("visa", "")
            if visa and hasattr(page, "visa_resource_combo"):
                if page.visa_resource_combo.findText(visa) < 0:
                    page.visa_resource_combo.addItem(visa)
                page.visa_resource_combo.setCurrentText(visa)
        if "chamber" in meta and self._chamber_widgets_built:
            chamber_type = meta["chamber"].get("type", "vt6002")
            if hasattr(page, "chamber_type_combo"):
                idx = page.chamber_type_combo.findData(chamber_type)
                if idx >= 0:
                    page.chamber_type_combo.setCurrentIndex(idx)
            port = meta["chamber"].get("port", "")
            if port and hasattr(page, "chamber_port_combo"):
                if page.chamber_port_combo.findText(port) < 0:
                    page.chamber_port_combo.addItem(port)
                page.chamber_port_combo.setCurrentText(port)
        if "uart" in meta and self._uart_widgets_built:
            port = meta["uart"].get("port", "")
            baud = meta["uart"].get("baud", "")
            if port and hasattr(page, "_sc_port_combo"):
                if page._sc_port_combo.findText(port) < 0:
                    page._sc_port_combo.addItem(port)
                page._sc_port_combo.setCurrentText(port)
            if baud and hasattr(page, "_sc_baud_combo"):
                page._sc_baud_combo.setCurrentText(baud)
        if "mcu_io" in meta and self._mcu_io_widgets_built:
            port = meta["mcu_io"].get("port", "")
            if port and hasattr(page, "mcu_io_port_combo"):
                if page.mcu_io_port_combo.findText(port) < 0:
                    page.mcu_io_port_combo.addItem(port, port)
                page.mcu_io_port_combo.setCurrentText(port)
        self._try_auto_connect_instruments(meta)
        self._pending_instr_meta = None

    def sync_external(self) -> None:
        if getattr(self._page, "_n6705c_top_ref", None):
            self.sync_n6705c_from_top()
        chamber_ui = getattr(self._page, "_chamber_ui_ref", None)
        if chamber_ui and getattr(chamber_ui, "chamber", None):
            self.on_chamber_external_changed()
        self.sync_mcu_io_from_manager()

    def sync_n6705c_from_top(self) -> None:
        page = self._page
        if not self._n6705c_widgets_built:
            top_ref = getattr(page, "_n6705c_top_ref", None)
            if top_ref and hasattr(top_ref, "is_connected_a"):
                if top_ref.is_connected_a and top_ref.n6705c_a:
                    page.n6705c = top_ref.n6705c_a
                    page.is_connected = True
            return
        page._sync_n6705c_from_top_mixin()

    def on_chamber_external_changed(self) -> None:
        page = self._page
        if not self._chamber_widgets_built:
            chamber_ui = getattr(page, "_chamber_ui_ref", None)
            if chamber_ui and getattr(chamber_ui, "chamber", None):
                chamber = chamber_ui.chamber
                is_open = (
                    chamber.is_connected()
                    if hasattr(chamber, "is_connected")
                    else hasattr(chamber, "ser") and chamber.ser.is_open
                )
                if is_open:
                    page.chamber = chamber
                    page.is_chamber_connected = True
            return
        page._on_chamber_external_changed_mixin()

    def on_manager_scan_finished(self, instrument_type: str, candidates: list) -> None:
        page = self._page
        if instrument_type != "mcu_io" or not self._mcu_io_widgets_built:
            return
        page.mcu_io_port_combo.clear()
        if candidates:
            for candidate in candidates:
                display = candidate.display_name or candidate.resource
                page.mcu_io_port_combo.addItem(display, candidate.resource)
            self._set_mcu_io_status(f"● Found {len(candidates)}", "ok")
            page.mcu_io_connect_btn.setEnabled(True)
        else:
            page.mcu_io_port_combo.addItem("No MCU IO ports found", "")
            self._set_mcu_io_status("● Not Found", "err")
            page.mcu_io_connect_btn.setEnabled(False)
        page.mcu_io_search_btn.setEnabled(True)

    def on_manager_scan_failed(self, instrument_type: str, error: str) -> None:
        page = self._page
        if instrument_type != "mcu_io" or not self._mcu_io_widgets_built:
            return
        self._set_mcu_io_status("● Search Failed", "err")
        page.mcu_io_search_btn.setEnabled(True)
        page.mcu_io_connect_btn.setEnabled(True)
        self._append_log(f"[MCU_IO] Search failed: {error}")

    def on_manager_session_connected(self, session_id: str) -> None:
        if session_id == "mcu_io:default":
            self.sync_mcu_io_from_manager()

    def on_manager_connection_failed(self, session_id: str, error: str) -> None:
        page = self._page
        if session_id == "mcu_io:default" and self._mcu_io_widgets_built:
            self._set_mcu_io_status("● Failed", "err")
            page.mcu_io_connect_btn.setEnabled(True)
            page.mcu_io_search_btn.setEnabled(True)
            self._append_log(f"[MCU_IO] Connection failed: {error}")

    def on_manager_session_disconnected(self, session_id: str) -> None:
        if session_id == "mcu_io:default":
            self.sync_mcu_io_from_manager()

    def sync_mcu_io_from_manager(self) -> None:
        page = self._page
        manager = getattr(page, "_instrument_manager", None)
        if not self._mcu_io_widgets_built or manager is None:
            return
        session = manager.get_session("mcu_io:default")
        if session and session.connected and session.instance:
            page.mcu_io = session.instance
            page.is_mcu_io_connected = True
            if hasattr(page, "mcu_io_port_combo") and session.resource:
                if page.mcu_io_port_combo.findText(session.resource) < 0:
                    page.mcu_io_port_combo.addItem(session.resource, session.resource)
                page.mcu_io_port_combo.setCurrentText(session.resource)
            self._set_mcu_io_status("● Connected", "ok")
            page.mcu_io_connect_btn.setEnabled(True)
            page.mcu_io_connect_btn.setText("Disconnect")
            page.mcu_io_search_btn.setEnabled(False)
        else:
            page.mcu_io = None
            page.is_mcu_io_connected = False
            self._set_mcu_io_status("● Disconnected", "err")
            page.mcu_io_connect_btn.setEnabled(True)
            page.mcu_io_connect_btn.setText("Connect")
            page.mcu_io_search_btn.setEnabled(True)

    def _try_auto_connect_instruments(self, meta: dict) -> None:
        if not meta:
            return
        page = self._page

        if "n6705c" in meta and self._n6705c_widgets_built:
            try:
                already = False
                if hasattr(page, "is_n6705c_connected"):
                    try:
                        already = bool(page.is_n6705c_connected())
                    except Exception:
                        already = bool(getattr(page, "is_connected", False))
                if not already and hasattr(page, "_on_n6705c_connect"):
                    self._append_log("[AUTO] 尝试连接 N6705C ...")
                    page._on_n6705c_connect()
            except Exception as exc:
                logger.warning("自动连接 N6705C 失败: %s", exc, exc_info=True)
                self._append_log(f"[AUTO] N6705C 自动连接失败: {exc}")

        if "chamber" in meta and self._chamber_widgets_built:
            try:
                already = False
                if hasattr(page, "is_chamber_connected_status"):
                    try:
                        already = bool(page.is_chamber_connected_status())
                    except Exception:
                        already = bool(getattr(page, "is_chamber_connected", False))
                if not already and hasattr(page, "_on_chamber_connect"):
                    self._append_log("[AUTO] 尝试连接 Chamber ...")
                    page._on_chamber_connect()
            except Exception as exc:
                logger.warning("自动连接 Chamber 失败: %s", exc, exc_info=True)
                self._append_log(f"[AUTO] Chamber 自动连接失败: {exc}")

        if "uart" in meta and self._uart_widgets_built:
            try:
                if not getattr(page, "_serial_connected", False) and hasattr(page, "_on_serial_connect"):
                    self._append_log("[AUTO] 尝试连接 UART ...")
                    page._on_serial_connect()
            except Exception as exc:
                logger.warning("自动连接 UART 失败: %s", exc, exc_info=True)
                self._append_log(f"[AUTO] UART 自动连接失败: {exc}")

        if "mcu_io" in meta and self._mcu_io_widgets_built:
            try:
                if not getattr(page, "is_mcu_io_connected", False):
                    self._append_log("[AUTO] 尝试连接 MCU IO ...")
                    self._on_mcu_io_connect()
            except Exception as exc:
                logger.warning("自动连接 MCU IO 失败: %s", exc, exc_info=True)
                self._append_log(f"[AUTO] MCU IO 自动连接失败: {exc}")

    def _build_mcu_io_connection_widgets(self) -> None:
        page = self._page
        box = QFrame()
        box.setStyleSheet("""
            QFrame {
                background-color: #0d1a36;
                border: 1px solid #1a2d57;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(6)

        page.mcu_io_status_label = QLabel("● Disconnected")
        page.mcu_io_status_label.setObjectName("statusErr")
        layout.addWidget(page.mcu_io_status_label)

        page.mcu_io_port_combo = DarkComboBox(bg="#091426", border="#17345f")
        page.mcu_io_port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        page.mcu_io_port_combo.addItem("Select MCU IO port", "")
        layout.addWidget(page.mcu_io_port_combo)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        page.mcu_io_search_btn = SpinningSearchButton(parent=box)
        page.mcu_io_search_btn.setFixedHeight(24)
        page.mcu_io_connect_btn = QPushButton("Connect")
        page.mcu_io_connect_btn.setFixedHeight(24)
        page.mcu_io_connect_btn.setStyleSheet(
            "QPushButton { background-color: #053b38; color: #10e7bc;"
            " border: 1px solid #08c9a5; border-radius: 6px;"
            " font-size: 11px; font-weight: 700; padding: 2px 8px; }"
            "QPushButton:hover { background-color: #064744; }"
            "QPushButton:disabled { background-color: #0D1734; color: #3a4a6a;"
            " border: 1px solid #18264A; }"
        )
        btn_row.addWidget(page.mcu_io_search_btn, 0)
        btn_row.addWidget(page.mcu_io_connect_btn, 1)
        layout.addLayout(btn_row)

        page.mcu_io_search_btn.clicked.connect(self._on_mcu_io_search)
        page.mcu_io_connect_btn.clicked.connect(self._on_mcu_io_connect_toggle)
        self._layout.addWidget(box)

    def _set_mcu_io_status(self, text: str, state: str = "err") -> None:
        page = self._page
        if not hasattr(page, "mcu_io_status_label"):
            return
        page.mcu_io_status_label.setText(text)
        obj = {
            "ok": "statusOk",
            "warn": "statusWarn",
            "err": "statusErr",
        }.get(state, "statusErr")
        page.mcu_io_status_label.setObjectName(obj)
        page.mcu_io_status_label.style().unpolish(page.mcu_io_status_label)
        page.mcu_io_status_label.style().polish(page.mcu_io_status_label)
        page.mcu_io_status_label.update()

    def _mcu_io_selected_resource(self) -> str:
        page = self._page
        if not hasattr(page, "mcu_io_port_combo"):
            return ""
        data = page.mcu_io_port_combo.currentData()
        if data:
            return str(data)
        text = page.mcu_io_port_combo.currentText()
        if text.startswith("Select ") or text.startswith("No "):
            return ""
        return text.split()[0] if text else ""

    def _on_mcu_io_search(self) -> None:
        page = self._page
        manager = getattr(page, "_instrument_manager", None)
        if manager is None:
            self._set_mcu_io_status("● No manager", "err")
            return
        self._set_mcu_io_status("● Searching", "warn")
        page.mcu_io_search_btn.setEnabled(False)
        page.mcu_io_connect_btn.setEnabled(False)
        manager.scan_async("mcu_io")

    def _on_mcu_io_connect_toggle(self) -> None:
        page = self._page
        if getattr(page, "is_mcu_io_connected", False):
            manager = getattr(page, "_instrument_manager", None)
            if manager is not None:
                manager.disconnect_async("mcu_io:default")
            return
        self._on_mcu_io_connect()

    def _on_mcu_io_connect(self) -> None:
        page = self._page
        resource = self._mcu_io_selected_resource()
        if not resource:
            self._set_mcu_io_status("● Select port first", "err")
            return
        manager = getattr(page, "_instrument_manager", None)
        if manager is None:
            self._set_mcu_io_status("● No manager", "err")
            return
        self._set_mcu_io_status("● Connecting", "warn")
        page.mcu_io_connect_btn.setEnabled(False)
        manager.connect_async(InstrumentSpec(
            instrument_type="mcu_io",
            role="mcu_io",
            connection_kind="serial_raw_repl",
            slot="default",
            resource=resource,
        ))

    def _clear_layout(self) -> None:
        while self._layout.count() > 0:
            child = self._layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
            elif child.layout():
                while child.layout().count():
                    sub = child.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()

    def _show_placeholder(self) -> None:
        placeholder = QLabel("No instruments in sequence")
        placeholder.setObjectName("placeholderText")
        self._layout.addWidget(placeholder)

    def _add_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        self._layout.addWidget(label)
        return label

    def _append_log(self, message: str) -> None:
        result_panel = getattr(self._page, "result_panel", None)
        if result_panel is not None:
            result_panel.append_log(message)

    def _set_built_flags(self, n6705c: bool, chamber: bool, uart: bool, mcu_io: bool) -> None:
        self._set_n6705c_built(n6705c)
        self._set_chamber_built(chamber)
        self._set_uart_built(uart)
        self._set_mcu_io_built(mcu_io)

    def _set_n6705c_built(self, value: bool) -> None:
        self._n6705c_widgets_built = value
        setattr(self._page, "_n6705c_widgets_built", value)

    def _set_chamber_built(self, value: bool) -> None:
        self._chamber_widgets_built = value
        setattr(self._page, "_chamber_widgets_built", value)

    def _set_uart_built(self, value: bool) -> None:
        self._uart_widgets_built = value
        setattr(self._page, "_uart_widgets_built", value)

    def _set_mcu_io_built(self, value: bool) -> None:
        self._mcu_io_widgets_built = value
        setattr(self._page, "_mcu_io_widgets_built", value)
