#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QButtonGroup, QRadioButton, QWidget
from debug_config import DEBUG_MOCK
from ui.pages.n6705c_power_analyzer import datalog_style as dss
from ui.widgets.config_memory import ConfigMemory
from ui.pages.n6705c_power_analyzer.datalog.helpers import _ANN_DEFAULT_FONT
from ui.pages.n6705c_power_analyzer.datalog.view_connection import ConnectionViewMixin
from ui.pages.n6705c_power_analyzer.datalog.view_layout import LayoutViewMixin
from ui.pages.n6705c_power_analyzer.datalog.view_channel_config import ChannelConfigViewMixin
from ui.pages.n6705c_power_analyzer.datalog.view_plot import PlotViewMixin
from ui.pages.n6705c_power_analyzer.datalog.view_recording import RecordingViewMixin
from ui.pages.n6705c_power_analyzer.datalog.view_markers import MarkersViewMixin
from ui.pages.n6705c_power_analyzer.datalog.view_labels import LabelsViewMixin
from ui.pages.n6705c_power_analyzer.datalog.view_time_offset import TimeOffsetViewMixin
from ui.pages.n6705c_power_analyzer.datalog.view_import_export import ImportExportViewMixin
from log_config import get_logger

logger = get_logger(__name__)

class N6705CDatalogUI(QWidget, ConnectionViewMixin, LayoutViewMixin, ChannelConfigViewMixin, PlotViewMixin, RecordingViewMixin, MarkersViewMixin, LabelsViewMixin, TimeOffsetViewMixin, ImportExportViewMixin):
    """N6705C Datalog 页面主壳：装配各视图 Mixin，持有信号 / 状态与初始化。"""

    connection_status_changed = Signal(bool)

    labels_panel_toggled = Signal(bool)

    # ---- 窗口位置记忆（仅独立窗口态生效）----
    _WINDOW_DEFAULT_SIZE = (800, 600)

    _WINDOW_MARGIN = 40

    def __init__(self, n6705c_top=None, instrument_manager=None, ui_action_registry=None):
        super().__init__()

        self._top = n6705c_top
        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry
        self.n6705c_a = None
        self.n6705c_b = None
        self.is_connected_a = False
        self.is_connected_b = False
        self.is_recording = False
        # 连接进行中槽位（slot_label -> visa_resource），防止同槽并发连接竞态
        self._pending_connects = {}
        # 槽位同步去重签名：(A连接态, A序列号, B连接态, B序列号)，无变化跳过重建
        self._last_slot_sync_sig = None
        self._last_conn_status_emitted = None

        self._record_thread = None
        self._record_worker = None
        # 一键引导覆盖层（GuideTourOverlay），None 表示未在引导中
        self._guide_tour = None

        self.datalog_data = {}
        self._raw_dlog_list = []
        self._imported_tab_configs = []
        self._import_counter = 0

        # 通道开关按钮列表：__init__ 即初始化为空列表，
        # 后续由 _refresh_channel_config 重建填充，各处不再防御性 getattr。
        self.ch_checkboxes_a = []
        self.ch_voltage_cbs_a = []
        self.ch_current_cbs_a = []
        self.ch_power_cbs_a = []
        self.ch_checkboxes_b = []
        self.ch_voltage_cbs_b = []
        self.ch_current_cbs_b = []
        self.ch_power_cbs_b = []

        self._band_info = {}
        self._band_grid_lines = []
        self._band_zero_lines = {}
        self._selected_ch_key = None
        self._selected_orig_pen = None
        self._selected_highlight = None
        self._ch_drag_active = False
        self._ch_drag_last_y = None
        self.marker_a_pos = None
        self.marker_b_pos = None
        self.marker_a_line = None
        self.marker_b_line = None
        self.marker_a_frozen = False
        self.marker_b_frozen = False
        self.marker_region = None
        self._extra_markers = []
        self._extra_marker_regions = []
        self._extra_marker_text_items = []
        self._marker_ab_text_item = None
        self._ab_ann_dx = 0.0
        self._ab_ann_dy = 0.0
        self._ab_ann_font = _ANN_DEFAULT_FONT
        self._marker_follow_line = None
        self.box_zoom_enabled = False
        self._b_time_offset = 0.0
        self._file_time_offsets = {}
        self._known_data_keys = set()
        self._tab_hidden_snapshot = {}
        self._box_zoom_auto_off_timer = QTimer(self)
        self._box_zoom_auto_off_timer.setSingleShot(True)
        self._box_zoom_auto_off_timer.setInterval(4000)
        self._box_zoom_auto_off_timer.timeout.connect(self._auto_off_box_zoom)
        self._pending_marker = None
        self._marker_drag_target = None
        self._marker_snap_px = 10
        self.custom_labels = []
        self.custom_label_lines = []
        self._label_time_last_unit = "s"

        self.crosshair_v = None
        self.crosshair_tooltip = None
        self.crosshair_dots = []

        self.type_current = QRadioButton()
        # 独立隐藏状态位：须关闭 autoExclusive，否则 QRadioButton 的
        # setChecked(False) 无效，配置记忆无法还原 False（电压类型）。
        self.type_current.setAutoExclusive(False)
        self.type_current.setChecked(True)
        self.type_current.hide()

        self.mode_group = QButtonGroup(self)
        self.mode_4ch = QRadioButton()
        self.mode_8ch = QRadioButton()
        self.mode_4ch.setChecked(True)
        self.mode_group.addButton(self.mode_4ch, 0)
        self.mode_group.addButton(self.mode_8ch, 1)

        self._setup_style()
        self._create_layout()
        self._init_ui_elements()
        self._bind_signals()

        if DEBUG_MOCK:
            self._add_default_debug_device()
            self._sync_device_card_states()
            self._update_time_offset_btn_visibility()
        else:
            self._add_default_saved_devices()
            self._sync_device_card_states()

        if self._top:
            self._sync_from_top()
            if hasattr(self._top, 'connection_changed'):
                self._top.connection_changed.connect(self._sync_from_top)

        if self._instrument_manager:
            self._instrument_manager.sessions_changed.connect(self._on_manager_sessions_changed)
            self._instrument_manager.connection_failed.connect(self._on_manager_connection_failed)
            self._instrument_manager.disconnect_failed.connect(self._on_manager_disconnect_failed)

        # 自动连接放在 top/manager 状态同步之后，避免对已连接设备重复发起
        self._auto_connect_enabled_cards()

        if not (self.is_connected_a or self.is_connected_b):
            self._show_left_panel("instrument")
        # §5b：登记本页无专用接口的按钮（Auto Fit / 导出 / 导入）为具名 UI 动作
        self._register_ai_ui_actions()

        # 上次测试配置自动记忆（仅回填控件值，不触发仪器连接）；
        # 4ch/8ch 为互斥组且默认 4ch，只 bind mode_8ch 即可双向还原；
        # Select All 勾选为派生状态，不单独持久化。
        self._config_memory = ConfigMemory("n6705c/datalog", self)
        self._config_memory.bind("mode_8ch", self.mode_8ch)
        self._config_memory.bind("type_current", self.type_current)
        self._config_memory.bind("min_period", self.min_period_cb)
        self._config_memory.bind("meas_minimum", self.meas_minimum_cb)
        self._config_memory.bind("meas_average", self.meas_average_cb)
        self._config_memory.bind("meas_maximum", self.meas_maximum_cb)
        self._config_memory.bind("meas_peak2peak", self.meas_peak2peak_cb)
        self._config_memory.bind("meas_charge_ah", self.meas_charge_ah_cb)
        self._config_memory.bind("meas_charge_c", self.meas_charge_c_cb)
        self._config_memory.bind("label_time", self.label_time_edit)
        self._config_memory.bind("label_text", self.label_text_edit)
        self._config_memory.restore()

    def _init_ui_elements(self):
        self._update_recording_button_state(False)
        if self.min_period_cb.isChecked():
            self.sample_period_edit.setReadOnly(True)
            self.sample_period_edit.setStyleSheet(dss.SAMPLE_PERIOD_READONLY_STYLE)

    def _bind_signals(self):
        self.start_btn.clicked.connect(self._on_start_or_stop_recording)
        self.export_btn.clicked.connect(self._on_export)
        self.import_btn.clicked.connect(self._on_import)

        self.box_zoom_btn.clicked.connect(self._toggle_box_zoom)
        self.reset_view_btn.clicked.connect(self._reset_view)
        self.marker_a_btn.clicked.connect(lambda: self._set_marker_mode("A"))
        self.marker_b_btn.clicked.connect(lambda: self._set_marker_mode("B"))
        self.marker_a_btn.customContextMenuRequested.connect(
            lambda pos: self._show_marker_btn_menu("A", pos)
        )
        self.marker_b_btn.customContextMenuRequested.connect(
            lambda pos: self._show_marker_btn_menu("B", pos)
        )
        self.add_markers_btn.clicked.connect(self._on_add_markers)
        self.clear_markers_btn.clicked.connect(self._clear_markers)
        self.time_offset_btn.clicked.connect(self._on_time_offset)

        self.add_label_btn.clicked.connect(self._add_custom_label)
        self.label_time_edit.returnPressed.connect(self._add_custom_label)
        self.label_text_edit.returnPressed.connect(self._add_custom_label)
        self.label_time_edit.editingFinished.connect(self._on_label_time_editing_finished)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_progress_overlay') and self._progress_overlay.isVisible():
            self._progress_overlay.setGeometry(self.chart_frame.rect())
        if hasattr(self, '_channel_config_overlay') and self._channel_config_overlay.isVisible():
            self._channel_config_overlay.setGeometry(self.channel_config_card.rect())

    def event(self, ev):
        if ev.type() == ev.Type.LayoutRequest:
            if hasattr(self, '_progress_overlay') and self._progress_overlay.isVisible():
                QTimer.singleShot(0, lambda: self._progress_overlay.setGeometry(self.chart_frame.rect()))
            if hasattr(self, '_channel_config_overlay') and self._channel_config_overlay.isVisible():
                QTimer.singleShot(0, lambda: self._channel_config_overlay.setGeometry(self.channel_config_card.rect()))
        return super().event(ev)

    def closeEvent(self, event):
        try:
            self._save_window_geometry()
        except Exception:
            logger.debug("Save window geometry on close failed", exc_info=True)
        # 停止进行中的录制 / 搜索 / 连接线程，避免关闭时 QThread 仍在运行
        if self._record_thread and self._record_thread.isRunning():
            if self._record_worker:
                self._record_worker.stop()
            self._record_thread.quit()
            self._record_thread.wait(3000)
        for attr in ("_scan_thread", "_connect_thread"):
            thread = getattr(self, attr, None)
            if thread is not None and thread.isRunning():
                thread.quit()
                thread.wait(2000)
        # 独立运行（无 top/manager 托管生命周期）时，关闭前断开本地持有的仪器
        if self._top is None and self._instrument_manager is None:
            for inst in (self.n6705c_a, self.n6705c_b):
                if inst is not None:
                    self._close_instrument(inst)
            self.n6705c_a = None
            self.n6705c_b = None
            self.is_connected_a = False
            self.is_connected_b = False
        super().closeEvent(event)
