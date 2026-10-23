#
# python -m ui.modules.serialCom_module.serialCom_module_frame
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

import os

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import (
    QTimer,
    Qt,
    Signal,
)
from log_config import get_logger
from core.auto_baud_detector import AutoBaudMonitor
from ui.modules.serialCom_module.serial_style import (
    DARK_CARD_STYLE,
    MODE_FULL,
    MODE_INLINE,
    MODE_SEARCH_SELECT,
    add_serial_port_item,
    body_splitter_style,
    center_vsplitter_style,
    center_widget_style,
)


logger = get_logger(__name__)

from ui.modules.serialCom_module.mixins.connection_mixin import ConnectionMixin
from ui.modules.serialCom_module.mixins.toolbar_mixin import ToolbarMixin
from ui.modules.serialCom_module.mixins.log_panel_mixin import LogPanelMixin
from ui.modules.serialCom_module.mixins.filter_save_mixin import FilterSaveMixin
from ui.modules.serialCom_module.mixins.send_mixin import SendMixin
from ui.modules.serialCom_module.mixins.chart_mixin import ChartMixin
from ui.modules.serialCom_module.mixins.script_mixin import ScriptMixin
from ui.modules.serialCom_module.mixins.persistence_mixin import PersistenceMixin


class SerialComMixin(ConnectionMixin, ToolbarMixin, LogPanelMixin, FilterSaveMixin,
                     SendMixin, ChartMixin, ScriptMixin, PersistenceMixin):
    serial_connection_changed = Signal(bool)
    serial_data_received = Signal(bytes)

    def complete_serialComWidget(self, parent_layout):
        self._sc_paused = False
        self._sc_stopped = False
        self._sc_rx_line_buf = ""
        self._sc_rx_flush_timer = None
        self._sc_show_line_num = False
        self._sc_highlight_keywords = []  # [{"keyword": str, "bg": str, "fg": str}]
        self._sc_max_log_lines = self._SC_MAX_LOG_LINES_DEFAULT
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
        self._sc_show_system_log = False
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
        self._sc_footer_visible = True
        self._sc_primary_panel_title = "Serial Log"
        self._sc_extra_log_panels = []
        self._sc_active_log_panel_index = 0

        self._sc_chart_config = None
        self._sc_chart_controller = None
        self._sc_chart_dialog = None

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
        self._sc_quick_area.setMinimumHeight(178)

        center_splitter.addWidget(top_section)
        center_splitter.addWidget(self._sc_quick_area)
        center_splitter.setStretchFactor(0, 1)
        center_splitter.setStretchFactor(1, 0)
        self._sc_center_splitter_default_sizes = [680, 185]
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
        self._sc_load_persisted_state()
        # 侧栏跟随聚焦面板：主面板 Serial 真值初始化（持久化回放后、首次焦点同步前）
        self._sc_primary_serial_cfg = self._sc_sidebar_serial_cfg_from_controls()
        self._sc_sidebar_bound_index = self._sc_active_log_panel_index
        self._sc_start_temp_log()
        self._sc_start_port_hotplug()
        self._sc_sync_top_control_state()


if __name__ == "__main__":
    #python -m ui.modules.serialCom_module.serialCom_module_frame
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
