#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFrame, QSizePolicy,
    QStackedWidget, QApplication, QTextEdit, QMenu, QFileDialog
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPixmap, QImage
from ui.widgets.dark_combobox import DarkComboBox

# DEBUG_MSO64B_FLAG = False
# DEBUG_DSOX4034A_FLAG = True

# DEBUG_MSO64B_FLAG = True
# DEBUG_DSOX4034A_FLAG = False

DEBUG_MSO64B_FLAG = False
DEBUG_DSOX4034A_FLAG = False


# ---------------------------------------------------------------------------
# TimeScale 序列输入框：支持鼠标滚轮按 1-2-4-10 序列在 ns/us/ms/s 单位间切换
# ---------------------------------------------------------------------------
class TimeScaleEdit(QLineEdit):
    """A QLineEdit that supports mouse wheel to cycle through a
    predefined time-scale sequence (1-2-4-10 pattern across ns/us/ms/s),
    while also allowing arbitrary text input.

    When Enter is pressed, the *returnPressed* signal fires so the
    parent UI can apply the value to the instrument.
    """

    # 完整的时间刻度序列（以秒为单位）
    SCALE_SEQUENCE = [
        1e-9, 2e-9, 4e-9, 10e-9, 20e-9, 40e-9, 100e-9, 200e-9, 400e-9,
        1e-6, 2e-6, 4e-6, 10e-6, 20e-6, 40e-6, 100e-6, 200e-6, 400e-6,
        1e-3, 2e-3, 4e-3, 10e-3, 20e-3, 40e-3, 100e-3, 200e-3, 400e-3,
        1.0, 2.0, 4.0, 10.0,
    ]

    # 单位后缀 -> 乘数
    _UNIT_MAP = {
        'ns': 1e-9,
        'us': 1e-6,
        'ms': 1e-3,
        's':  1.0,
    }

    def __init__(self, default_text="1us", parent=None):
        super().__init__(default_text, parent)
        self._current_index = self._find_nearest_index(self.parse_to_seconds(default_text))

    # -- 公开 API --------------------------------------------------------------

    def value_in_seconds(self) -> float:
        """解析当前文本并返回以秒为单位的浮点数。"""
        return self.parse_to_seconds(self.text())

    @classmethod
    def parse_to_seconds(cls, text: str) -> float:
        """将带单位的字符串解析为秒值。
        支持格式： '1us', '400ns', '10ms', '2s', 或纯数字（默认单位为秒）。
        """
        t = text.strip().lower()
        for suffix, mult in sorted(cls._UNIT_MAP.items(), key=lambda x: -len(x[0])):
            if t.endswith(suffix):
                num_str = t[:-len(suffix)].strip()
                try:
                    return float(num_str) * mult
                except ValueError:
                    return 1e-6  # 解析失败时的默认值
        # 没有单位后缀，尝试作为纯数字（秒）
        try:
            return float(t)
        except ValueError:
            return 1e-6

    @classmethod
    def seconds_to_display(cls, seconds: float) -> str:
        """将秒值转换为可读的带单位字符串。"""
        abs_val = abs(seconds)
        if abs_val < 1e-6:
            val = seconds / 1e-9
            unit = 'ns'
        elif abs_val < 1e-3:
            val = seconds / 1e-6
            unit = 'us'
        elif abs_val < 1.0:
            val = seconds / 1e-3
            unit = 'ms'
        else:
            val = seconds
            unit = 's'
        # 如果是整数就不显示小数点
        if val == int(val):
            return f"{int(val)}{unit}"
        return f"{val:g}{unit}"

    # -- 内部方法 --------------------------------------------------------------

    def _find_nearest_index(self, seconds: float) -> int:
        """找到序列中最接近 seconds 的索引。"""
        best = 0
        best_diff = abs(self.SCALE_SEQUENCE[0] - seconds)
        for i, v in enumerate(self.SCALE_SEQUENCE):
            diff = abs(v - seconds)
            if diff < best_diff:
                best = i
                best_diff = diff
        return best

    def wheelEvent(self, event):
        """鼠标滚轮滚动时按序列切换时间刻度值。"""
        delta = event.angleDelta().y()
        if delta == 0:
            return

        # 先根据当前文本重新定位索引
        current_seconds = self.parse_to_seconds(self.text())
        self._current_index = self._find_nearest_index(current_seconds)

        if delta > 0:
            # 滚轮向上 -> 增大时间刻度
            self._current_index = min(self._current_index + 1, len(self.SCALE_SEQUENCE) - 1)
        else:
            # 滚轮向下 -> 减小时间刻度
            self._current_index = max(self._current_index - 1, 0)

        new_val = self.SCALE_SEQUENCE[self._current_index]
        self.setText(self.seconds_to_display(new_val))
        event.accept()


class OscilloscopeBaseUI(QWidget):

    INSTRUMENT_TITLE = "Oscilloscope"
    NUM_CHANNELS = 4
    RESOURCE_PLACEHOLDER = "VISA Resource / IP Address"
    TIMESCALE_DEFAULT = "1us"
    TRIGGER_LEVEL_DEFAULT = "1.25"
    CHANNEL_SCALE_DEFAULT = "1"
    CHANNEL_OFFSET_DEFAULT = "0"
    CHANNEL_OFFSET_LABEL = "Offset (V)"
    TRIGGER_SLOPE_OPTIONS = ["POS", "NEG", "EITH"]
    METRIC_DEFAULTS = [
        ("CH1 Vpp", "– –"),
        ("CH1 Freq", "– –"),
        ("CH2 Vmax", "– –"),
        ("CH2 Vmin", "– –"),
    ]

    CHANNEL_COLORS = {
        1: "#F0B400",
        2: "#4C8DFF",
        3: "#00C896",
        4: "#9E7BFF",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.channels = []
        self.channel_cards = []
        self.channel_tab_buttons = []
        self.is_connected = False
        self.rm = None
        self.available_devices = []

        self.search_timer = QTimer(self)
        self.search_timer.timeout.connect(self._search_devices)
        self.search_timer.setSingleShot(True)

        self._setup_fonts()
        self._setup_style()
        self._init_layout()
        self._init_ui_elements()

    def _setup_fonts(self):
        self.base_font = QFont("Segoe UI", 10)
        self.title_font = QFont("Segoe UI", 18, QFont.Bold)
        self.section_font = QFont("Segoe UI", 12, QFont.Bold)
        self.value_font = QFont("Segoe UI", 11)

    def _setup_style(self):
        self.setObjectName("rootWidget")
        self.setStyleSheet("""
            QWidget#rootWidget {
                background-color: #020B2D;
                color: #D6DEF7;
                font-family: "Segoe UI";
                font-size: 10pt;
            }

            QLabel {
                color: #D6DEF7;
                background: transparent;
                border: none;
            }

            QFrame#card {
                background-color: #0B1638;
                border: 1px solid #16254A;
                border-radius: 16px;
            }

            QFrame#innerCard {
                background-color: #06112E;
                border: 1px solid #1A2A54;
                border-radius: 12px;
            }

            QFrame#captureArea {
                background-color: #000000;
                border: 1px solid #1B2E57;
                border-radius: 12px;
            }

            QLabel#pageTitle {
                color: #F3F6FF;
                font-size: 20pt;
                font-weight: 700;
            }

            QLabel#sectionTitle {
                color: #F0F4FF;
                font-size: 12pt;
                font-weight: 700;
            }

            QLabel#subTitle {
                color: #7F96C7;
                font-size: 9pt;
                font-weight: 700;
                letter-spacing: 1px;
            }

            QLabel#mutedText {
                color: #7B8CB7;
            }

            QLabel#statusDot {
                color: #5E719B;
                font-size: 11pt;
            }

            QLineEdit, QComboBox {
                background-color: #091735;
                border: 1px solid #1A2D57;
                border-radius: 8px;
                padding: 8px 10px;
                color: #DDE6FF;
                min-height: 20px;
            }

            QLineEdit:focus, QComboBox:focus {
                border: 1px solid #4C6FFF;
            }

            QPushButton {
                background-color: #13244A;
                color: #DDE6FF;
                border: 1px solid #22376A;
                border-radius: 8px;
                padding: 8px 14px;
                font-weight: 600;
            }

            QPushButton:hover {
                background-color: #182D5C;
            }

            QPushButton:pressed {
                background-color: #102040;
            }

            QPushButton:disabled {
                background-color: #0D1734;
                color: #5C6B95;
                border: 1px solid #18264A;
            }

            QPushButton#dynamicConnectBtn {
                border-radius: 8px;
                padding: 4px 14px;
                font-weight: 700;
            }

            QPushButton#dynamicConnectBtn[connected="false"] {
                background-color: #053b38;
                border: 1px solid #08c9a5;
                color: #10e7bc;
            }

            QPushButton#dynamicConnectBtn[connected="false"]:hover {
                background-color: #064744;
                border: 1px solid #19f0c5;
                color: #43f3d0;
            }

            QPushButton#dynamicConnectBtn[connected="false"]:pressed {
                background-color: #042f2d;
            }

            QPushButton#dynamicConnectBtn[connected="true"] {
                background-color: #3a0828;
                border: 1px solid #d61b67;
                color: #ffb7d3;
            }

            QPushButton#dynamicConnectBtn[connected="true"]:hover {
                background-color: #4a0b31;
                border: 1px solid #f0287b;
                color: #ffd0e2;
            }

            QPushButton#dynamicConnectBtn[connected="true"]:pressed {
                background-color: #330722;
            }

            QPushButton#searchBtn {
                padding: 4px 10px;
                border-radius: 8px;
                background-color: #13254b;
                border: 1px solid #22376A;
                color: #dce7ff;
                font-weight: 600;
            }

            QPushButton#searchBtn:hover {
                background-color: #1C2D55;
            }

            QPushButton#searchBtn:disabled {
                background-color: #0b1430;
                color: #5c7096;
                border: 1px solid #1a2850;
            }

            QLabel#statusOk {
                color: #10e7bc;
                font-weight: 700;
                font-size: 10pt;
            }

            QLabel#statusErr {
                color: #ff6b8a;
                font-weight: 700;
                font-size: 10pt;
            }

            QLabel#statusWarn {
                color: #f0b400;
                font-weight: 700;
                font-size: 10pt;
            }

            QPushButton#ghostBtn {
                background-color: #1A2750;
                border: 1px solid #22376A;
                color: #7F96C7;
                padding: 7px 14px;
            }

            QPushButton#ghostBtn:hover {
                background-color: #243B6E;
                border: 1px solid #3A5A9F;
                color: #A8BBDB;
            }

            QPushButton#ghostBtn:pressed {
                background-color: #162040;
            }

            QPushButton#primaryBtn {
                background-color: #3D33A6;
                border: none;
                color: #E8E9FF;
                padding: 10px 18px;
                font-weight: 700;
                border-radius: 10px;
            }

            QPushButton#primaryBtn:hover {
                background-color: #4B40BF;
            }

            QPushButton#channelTab {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                padding: 6px 8px;
                color: #5F77AE;
                font-weight: 700;
            }

            QPushButton#channelTab:checked {
                background-color: #F0B400;
                color: #081126;
            }

            QPushButton#segBtn {
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 6px 8px;
                color: #6E84B5;
                font-weight: 700;
            }

            QPushButton#segBtn:checked {
                background-color: #243760;
                color: #DDE6FF;
            }

            QSlider::groove:horizontal {
                height: 6px;
                border-radius: 3px;
                background: #2A3557;
            }

            QSlider::sub-page:horizontal {
                height: 6px;
                border-radius: 3px;
                background: #6E7A9C;
            }

            QSlider::handle:horizontal {
                background: #9AA6C5;
                border: none;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }

            QFrame#metricCard {
                background-color: #020C2A;
                border: 1px solid #16254A;
                border-radius: 12px;
            }

            QLabel#metricTitle {
                color: #90A7D8;
                font-size: 9pt;
                font-weight: 700;
            }

            QLabel#metricValue {
                color: #F3F6FF;
                font-size: 12pt;
                font-weight: 700;
            }

            QFrame#toggleTrack {
                background-color: #6D5710;
                border-radius: 10px;
            }

            QLabel#toggleKnob {
                background-color: #A0A9C6;
                border-radius: 7px;
                min-width: 14px;
                min-height: 14px;
                max-width: 14px;
                max-height: 14px;
            }

            QFrame#logContainer {
                background-color: #0B1638;
                border: 1px solid #16254A;
                border-radius: 16px;
            }

            QTextEdit#logEdit {
                background-color: #060E28;
                border: 1px solid #1A2A54;
                border-radius: 10px;
                color: #A8BBDB;
                font-family: "Consolas", "Courier New", monospace;
                font-size: 9pt;
                padding: 8px;
            }

            QPushButton#smallActionBtn {
                background-color: #162340;
                border: 1px solid #22376A;
                border-radius: 6px;
                color: #7F96C7;
                padding: 4px 10px;
                font-size: 9pt;
                font-weight: 600;
            }

            QPushButton#smallActionBtn:hover {
                background-color: #1C2D55;
            }
        """)

    def _init_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(14, 12, 14, 12)
        root_layout.setSpacing(14)

        root_layout.addLayout(self._create_top_bar())

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        left_layout = QVBoxLayout()
        left_layout.setSpacing(16)
        left_layout.addWidget(self._create_display_card(), 3)
        left_layout.addWidget(self._create_measurements_card(), 1)
        left_layout.addWidget(self._create_log_card(), 1)

        right_panel = self._create_settings_card()

        content_layout.addLayout(left_layout, 75)
        content_layout.addWidget(right_panel, 25)

        root_layout.addLayout(content_layout)

    def _create_top_bar(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        title_row.setSpacing(10)

        icon_label = QLabel("∿")
        icon_label.setStyleSheet("color:#7B7DFF; font-size:20px; font-weight:700;")
        title_row.addWidget(icon_label)

        self.title_label = QLabel(self.INSTRUMENT_TITLE)
        self.title_label.setObjectName("pageTitle")
        title_row.addWidget(self.title_label)
        title_row.addStretch()

        self.system_status_label = QLabel("● Ready")
        self.system_status_label.setObjectName("statusOk")
        title_row.addWidget(self.system_status_label)

        layout.addLayout(title_row)

        self.instrument_info_label = QLabel("")
        self.instrument_info_label.setObjectName("mutedText")
        self.instrument_info_label.setWordWrap(True)
        layout.addWidget(self.instrument_info_label)

        control_row = QHBoxLayout()
        control_row.setSpacing(10)

        self.visa_resource_combo = DarkComboBox(bg="#091735", border="#1A2D57")
        self.visa_resource_combo.setMinimumWidth(380)
        self.visa_resource_combo.setFixedHeight(36)
        self.visa_resource_combo.setEditable(True)
        if DEBUG_MSO64B_FLAG:
            self.visa_resource_combo.addItem("192.168.3.27")
        elif DEBUG_DSOX4034A_FLAG:
            self.visa_resource_combo.addItem("USB0::0x0957::0x17A4::MY61500152::INSTR")
        control_row.addWidget(self.visa_resource_combo, 1)

        self.search_btn = QPushButton("Search")
        self.search_btn.setObjectName("searchBtn")
        self.search_btn.setFixedHeight(36)
        self.search_btn.clicked.connect(self._on_search)
        control_row.addWidget(self.search_btn, 0)

        self.connect_btn = QPushButton("🔗  Connect")
        self.connect_btn.setObjectName("dynamicConnectBtn")
        self.connect_btn.setProperty("connected", "false")
        self.connect_btn.setFixedSize(140, 36)
        control_row.addWidget(self.connect_btn, 0)

        control_row.addStretch()

        layout.addLayout(control_row)
        return layout

    def _create_display_card(self):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("📷 Display Capture")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        self.capture_btn = QPushButton("⇩ 获取截图")
        self.capture_btn.setObjectName("ghostBtn")
        header.addWidget(self.capture_btn)

        self.invert_btn = QPushButton("◑ 反相")
        self.invert_btn.setCheckable(True)
        self.invert_btn.setChecked(False)
        self.invert_btn.setObjectName("ghostBtn")
        self.invert_btn.setToolTip("勾选后截图反转背景色（白底黑字）")
        self.invert_btn.setStyleSheet("""
            QPushButton {
                background-color: #1A2750;
                border: 1px solid #22376A;
                color: #7F96C7;
                padding: 7px 14px;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #243B6E;
                border: 1px solid #3A5A9F;
                color: #A8BBDB;
            }
            QPushButton:checked {
                background-color: #2A1A60;
                border: 1px solid #5B3FBF;
                color: #C4A8FF;
            }
            QPushButton:checked:hover {
                background-color: #351F75;
                border: 1px solid #6E4FD9;
                color: #D8C0FF;
            }
            QPushButton:disabled {
                background-color: #0E1628;
                border: 1px solid #151E35;
                color: #3A4563;
            }
        """)
        header.addWidget(self.invert_btn)

        layout.addLayout(header)

        self.display_placeholder = QFrame()
        self.display_placeholder.setObjectName("captureArea")
        capture_layout = QVBoxLayout(self.display_placeholder)
        capture_layout.setContentsMargins(0, 0, 0, 0)

        self.capture_image_label = QLabel()
        self.capture_image_label.setAlignment(Qt.AlignCenter)
        self.capture_image_label.setStyleSheet("background: transparent;")
        self.capture_image_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.capture_image_label.customContextMenuRequested.connect(self._on_capture_context_menu)
        self.capture_image_label.hide()
        self._current_pixmap = None
        capture_layout.addWidget(self.capture_image_label)

        self.capture_placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.capture_placeholder_widget)
        placeholder_layout.setContentsMargins(0, 0, 0, 0)
        placeholder_layout.setSpacing(10)
        placeholder_layout.setAlignment(Qt.AlignCenter)

        camera_icon = QLabel("📷")
        camera_icon.setAlignment(Qt.AlignCenter)
        camera_icon.setStyleSheet("font-size: 28px; color: #22355D;")
        placeholder_layout.addWidget(camera_icon)

        self.capture_hint_label = QLabel("No screenshot captured")
        self.capture_hint_label.setAlignment(Qt.AlignCenter)
        self.capture_hint_label.setStyleSheet("color: #314A7A; font-size: 11pt;")
        placeholder_layout.addWidget(self.capture_hint_label)

        capture_layout.addWidget(self.capture_placeholder_widget)

        self.display_placeholder.setMinimumHeight(220)
        layout.addWidget(self.display_placeholder)

        return card

    def _create_measurements_card(self):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)

        header = QHBoxLayout()
        title = QLabel("∿ Measurements")
        title.setObjectName("sectionTitle")
        header.addWidget(title)
        header.addStretch()

        self.measure_btn = QPushButton("↻ 刷新测量结果")
        self.measure_btn.setObjectName("ghostBtn")
        header.addWidget(self.measure_btn)
        layout.addLayout(header)

        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)

        self.metric_cards = []
        for title_text, value_text in self.METRIC_DEFAULTS:
            mc = self._create_metric_card(title_text, value_text)
            self.metric_cards.append(mc)
            metrics_layout.addWidget(mc)

        layout.addLayout(metrics_layout)
        return card

    def _create_metric_card(self, title_text, value_text):
        card = QFrame()
        card.setObjectName("metricCard")
        card.setMinimumHeight(64)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel(title_text)
        title.setObjectName("metricTitle")
        title.setAlignment(Qt.AlignCenter)

        value = QLabel(value_text)
        value.setObjectName("metricValue")
        value.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(value)

        card.title_label = title
        card.value_label = value
        return card

    def _create_settings_card(self):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(18)

        title = QLabel("\u2630 Oscilloscope Settings")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        layout.addWidget(self._create_small_section_title("HORIZONTAL"))
        h_box = QVBoxLayout()
        h_box.setSpacing(8)

        h_title = QLabel("TimeScale (s/div)")
        h_title.setStyleSheet("font-weight: 600; color:#B8C7EA;")
        h_box.addWidget(h_title)

        self.timebase_edit = TimeScaleEdit(self.TIMESCALE_DEFAULT)
        self.timebase_edit.setPlaceholderText("\u4f8b\u5982: 1us, 400ns, 10ms ...")
        self.timebase_edit.setToolTip("\u6eda\u8f6e\u8c03\u6574\u65f6\u95f4\u523b\u5ea6\uff0c\u6216\u76f4\u63a5\u8f93\u5165\u540e\u6309 Enter \u5e94\u7528")
        h_box.addWidget(self.timebase_edit)

        layout.addLayout(h_box)

        layout.addWidget(self._create_small_section_title("VERTICAL"))

        tab_bar = QFrame()
        tab_bar.setObjectName("innerCard")
        tab_layout = QHBoxLayout(tab_bar)
        tab_layout.setContentsMargins(4, 4, 4, 4)
        tab_layout.setSpacing(4)

        for i in range(self.NUM_CHANNELS):
            btn = QPushButton(f"CH{i+1}")
            btn.setObjectName("channelTab")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self._switch_channel_card(idx))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.channel_tab_buttons.append(btn)
            tab_layout.addWidget(btn)

        layout.addWidget(tab_bar)

        self.channel_stack = QStackedWidget()
        for i in range(self.NUM_CHANNELS):
            page = self._create_channel_card(i + 1)
            self.channel_stack.addWidget(page)
        layout.addWidget(self.channel_stack)

        layout.addSpacing(6)
        layout.addWidget(self._create_small_section_title("TRIGGER"))

        trigger_layout = QVBoxLayout()
        trigger_layout.setSpacing(10)

        trigger_layout.addWidget(self._labeled_widget("Source", self._create_trigger_source()))

        trigger_layout.addWidget(self._labeled_widget("Level (V)", self._create_trigger_level()))

        self.trigger_slope_combo = DarkComboBox(bg="#091735", border="#1A2D57")
        self.trigger_slope_combo.addItems(self.TRIGGER_SLOPE_OPTIONS)
        trigger_layout.addWidget(self._labeled_widget("Slope", self.trigger_slope_combo))

        layout.addLayout(trigger_layout)

        self.apply_btn = QPushButton("Apply Settings to Instrument")
        self.apply_btn.setObjectName("primaryBtn")
        self.apply_btn.setMinimumHeight(36)
        layout.addSpacing(6)
        layout.addWidget(self.apply_btn)

        # TimeScale 输入框敲击回车时，触发 Apply 按钮点击
        self.timebase_edit.returnPressed.connect(self.apply_btn.click)

        self.channel_tab_buttons[0].setChecked(True)
        self._switch_channel_card(0)

        return card

    def _create_small_section_title(self, text):
        label = QLabel(text)
        label.setObjectName("subTitle")
        return label

    def _create_trigger_source(self):
        self.trigger_source_combo = DarkComboBox(bg="#091735", border="#1A2D57")
        items = [f"CH{i+1}" for i in range(self.NUM_CHANNELS)] + ["EXT"]
        self.trigger_source_combo.addItems(items)
        return self.trigger_source_combo

    def _create_trigger_level(self):
        self.trigger_level_edit = QLineEdit(self.TRIGGER_LEVEL_DEFAULT)
        return self.trigger_level_edit

    def _labeled_widget(self, label_text, widget):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setStyleSheet("color:#AFC0E8; font-weight:600;")
        layout.addWidget(label)
        layout.addWidget(widget)
        return wrapper

    def _create_channel_card(self, channel_num):
        frame = QFrame()
        frame.setObjectName("innerCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()

        channel_label = QLabel(f"CH{channel_num}")
        channel_label.setStyleSheet(
            f"font-weight: 800; font-size: 12pt; color: {self.CHANNEL_COLORS.get(channel_num, '#DDE6FF')};"
        )
        header.addWidget(channel_label)
        header.addStretch()

        toggle_wrap = self._create_fake_toggle()
        header.addWidget(toggle_wrap["widget"])

        layout.addLayout(header)

        coupling_title = QLabel("Coupling")
        coupling_title.setStyleSheet("color:#AFC0E8; font-weight:600;")
        layout.addWidget(coupling_title)

        coupling_bar = QFrame()
        coupling_bar.setObjectName("innerCard")
        coupling_layout = QHBoxLayout(coupling_bar)
        coupling_layout.setContentsMargins(4, 4, 4, 4)
        coupling_layout.setSpacing(4)

        coupling_dc = QPushButton("DC")
        coupling_dc.setObjectName("segBtn")
        coupling_dc.setCheckable(True)
        coupling_dc.setChecked(True)

        coupling_ac = QPushButton("AC")
        coupling_ac.setObjectName("segBtn")
        coupling_ac.setCheckable(True)

        coupling_gnd = QPushButton("GND")
        coupling_gnd.setObjectName("segBtn")
        coupling_gnd.setCheckable(True)
        coupling_gnd.setEnabled(False)

        for btn in (coupling_dc, coupling_ac, coupling_gnd):
            btn.setAutoExclusive(True)
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            coupling_layout.addWidget(btn)

        layout.addWidget(coupling_bar)

        channel_data = {
            'toggle': toggle_wrap["button"],
            'coupling_combo': None,
            'coupling_dc': coupling_dc,
            'coupling_ac': coupling_ac,
            'coupling_gnd': coupling_gnd,
        }

        scale_widget = self._labeled_line_edit("Scale (V/div)", self.CHANNEL_SCALE_DEFAULT)
        offset_widget = self._labeled_line_edit(self.CHANNEL_OFFSET_LABEL, self.CHANNEL_OFFSET_DEFAULT)

        layout.addWidget(scale_widget["widget"])
        layout.addWidget(offset_widget["widget"])

        channel_data['scale_edit'] = scale_widget["edit"]
        channel_data['offset_edit'] = offset_widget["edit"]

        self.channels.append(channel_data)
        self.channel_cards.append(frame)
        return frame

    def _create_fake_toggle(self):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        btn = QPushButton()
        btn.setCheckable(True)
        btn.setChecked(True)
        btn.setFixedSize(30, 18)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #8A6A12;
                border: none;
                border-radius: 9px;
            }
            QPushButton:!checked {
                background-color: #33415F;
            }
        """)
        layout.addWidget(btn)

        return {"widget": container, "button": btn}

    def _labeled_line_edit(self, label_text, default_text):
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        label = QLabel(label_text)
        label.setStyleSheet("color:#AFC0E8; font-weight:600;")

        edit = QLineEdit(default_text)

        layout.addWidget(label)
        layout.addWidget(edit)

        return {"widget": wrapper, "edit": edit}

    def _switch_channel_card(self, index):
        for i, btn in enumerate(self.channel_tab_buttons):
            btn.setChecked(i == index)
        self.channel_stack.setCurrentIndex(index)

    def _init_ui_elements(self):
        for channel in self.channels:
            channel['scale_edit'].setText(self.CHANNEL_SCALE_DEFAULT)
            channel['offset_edit'].setText(self.CHANNEL_OFFSET_DEFAULT)
        self.append_log("[SYSTEM] Ready. Waiting for instrument connection.")

    def _create_log_card(self):
        card = QFrame()
        card.setObjectName("logContainer")
        log_layout = QVBoxLayout(card)
        log_layout.setContentsMargins(18, 16, 18, 18)
        log_layout.setSpacing(10)

        log_header = QHBoxLayout()

        log_title = QLabel("⊙ Execution Logs")
        log_title.setObjectName("sectionTitle")
        log_header.addWidget(log_title)
        log_header.addStretch()

        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.setObjectName("smallActionBtn")
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        log_header.addWidget(self.clear_log_btn)

        log_layout.addLayout(log_header)

        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("logEdit")
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(120)
        log_layout.addWidget(self.log_edit)

        return card

    def append_log(self, message):
        self.log_edit.append(message)

    def _on_clear_log(self):
        self.log_edit.clear()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_connection_info(self):
        return {
            'resource': self.visa_resource_combo.currentText()
        }

    def get_channel_settings(self, channel_num):
        if 1 <= channel_num <= self.NUM_CHANNELS:
            channel = self.channels[channel_num - 1]
            coupling = "DC"
            if channel.get("coupling_ac") and channel["coupling_ac"].isChecked():
                coupling = "AC"
            elif channel.get("coupling_gnd") and channel["coupling_gnd"].isChecked():
                coupling = "GND"

            result = {
                'enabled': channel['toggle'].isChecked(),
                'scale': float(channel['scale_edit'].text()),
                'offset': float(channel['offset_edit'].text()),
                'coupling': coupling,
            }

            return result
        return None

    def get_trigger_settings(self):
        return {
            'source': self.trigger_source_combo.currentText(),
            'level': float(self.trigger_level_edit.text()),
            'slope': self.trigger_slope_combo.currentText(),
        }

    def get_measure_settings(self):
        return {
            'channel': 1,
            'type': 'PK2PK'
        }

    def update_measure_result(self, measure_type, value):
        if len(self.metric_cards) < 4:
            return
        if measure_type == 'PK2PK':
            self.metric_cards[0].title_label.setText("Vpp")
            self.metric_cards[0].value_label.setText(f"{value:.6f} V")
        elif measure_type == 'FREQUENCY':
            self.metric_cards[1].title_label.setText("Freq")
            self.metric_cards[1].value_label.setText(f"{value:.2f} Hz")
        elif measure_type == 'VMAX':
            self.metric_cards[2].title_label.setText("Vmax")
            self.metric_cards[2].value_label.setText(f"{value:.6f} V")
        elif measure_type == 'VMIN':
            self.metric_cards[3].title_label.setText("Vmin")
            self.metric_cards[3].value_label.setText(f"{value:.6f} V")
        elif measure_type == 'MEAN':
            self.metric_cards[0].title_label.setText("Mean")
            self.metric_cards[0].value_label.setText(f"{value:.6f} V")
        elif measure_type == 'RMS':
            self.metric_cards[3].title_label.setText("RMS")
            self.metric_cards[3].value_label.setText(f"{value:.6f} V")
        elif measure_type == 'AMPLITUDE':
            self.metric_cards[2].title_label.setText("Amplitude")
            self.metric_cards[2].value_label.setText(f"{value:.6f} V")

    def update_connection_status(self, connected, instrument_info=None):
        self._update_connect_button_state(connected)
        if connected:
            self.search_btn.setEnabled(False)
            text = instrument_info if instrument_info else "Connected"
            self.instrument_info_label.setText(text)
            self.set_system_status("● Connected")
            self.append_log(f"[SYSTEM] Connected: {text}")
        else:
            self.search_btn.setEnabled(True)
            self.instrument_info_label.setText("")
            self.set_system_status("● Ready")
            self.append_log("[SYSTEM] Disconnected.")

    def update_display_image(self, png_bytes: bytes):
        if not png_bytes:
            return
        img = QImage()
        img.loadFromData(png_bytes, "PNG")
        if img.isNull():
            self.append_log("[ERROR] Failed to decode screenshot image.")
            return
        pixmap = QPixmap.fromImage(img)
        self._current_pixmap = pixmap
        scaled = pixmap.scaled(
            self.display_placeholder.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.capture_image_label.setPixmap(scaled)
        self.capture_image_label.show()
        self.capture_placeholder_widget.hide()
        self.append_log("[INFO] Screenshot captured and displayed.")

    def _on_capture_context_menu(self, pos):
        if self._current_pixmap is None:
            return
        menu = QMenu(self)
        copy_action = menu.addAction("📋 复制到剪贴板")
        save_action = menu.addAction("💾 另存为图片...")
        action = menu.exec(self.capture_image_label.mapToGlobal(pos))
        if action == copy_action:
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self._current_pixmap)
            self.append_log("[INFO] Screenshot copied to clipboard.")
        elif action == save_action:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "保存截图", "screenshot.png",
                "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)"
            )
            if file_path:
                self._current_pixmap.save(file_path)
                self.append_log(f"[INFO] Screenshot saved to: {file_path}")

    def set_invert_enabled(self, enabled: bool):
        self.invert_btn.setEnabled(enabled)
        if not enabled:
            self.invert_btn.setChecked(False)

    def _update_connect_button_state(self, connected: bool):
        self.is_connected = connected
        self.connect_btn.setProperty("connected", "true" if connected else "false")
        self.connect_btn.setText("⟲  Disconnect" if connected else "🔗  Connect")
        self.connect_btn.style().unpolish(self.connect_btn)
        self.connect_btn.style().polish(self.connect_btn)
        self.connect_btn.update()

    def set_system_status(self, status, is_error=False):
        self.system_status_label.setText(status)
        if is_error:
            self.system_status_label.setObjectName("statusErr")
        elif "Warning" in status or "Searching" in status:
            self.system_status_label.setObjectName("statusWarn")
        else:
            self.system_status_label.setObjectName("statusOk")
        self.system_status_label.style().unpolish(self.system_status_label)
        self.system_status_label.style().polish(self.system_status_label)
        self.system_status_label.update()

    def _on_search(self):
        self.set_system_status("● Searching")
        self.append_log("[SYSTEM] Scanning VISA / network resources...")
        self.search_btn.setEnabled(False)
        self.search_timer.start(100)

    def _search_devices(self):
        try:
            import pyvisa
            if self.rm is None:
                try:
                    self.rm = pyvisa.ResourceManager()
                except Exception:
                    self.rm = pyvisa.ResourceManager('@ni')

            self.available_devices = list(self.rm.list_resources()) or []

            scope_devices = []
            for dev in self.available_devices:
                try:
                    instr = self.rm.open_resource(dev, timeout=2000)
                    idn = instr.query('*IDN?').strip()
                    instr.close()
                    scope_devices.append(dev)
                    self.append_log(f"[SCAN] {dev} → {idn}")
                except Exception:
                    pass

            self.visa_resource_combo.setEnabled(True)
            self.visa_resource_combo.clear()

            if scope_devices:
                for dev in scope_devices:
                    self.visa_resource_combo.addItem(dev)
                count = len(scope_devices)
                self.set_system_status(f"● Found {count} device(s)")
                self.append_log(f"[SYSTEM] Found {count} VISA device(s).")
                self.visa_resource_combo.setCurrentIndex(0)
            else:
                self.visa_resource_combo.addItem("No device found")
                self.visa_resource_combo.setEnabled(False)
                self.set_system_status("● No device found", is_error=True)
                self.append_log("[SYSTEM] No VISA instrument found.")
        except Exception as e:
            self.set_system_status("● Search failed", is_error=True)
            self.append_log(f"[ERROR] Search failed: {str(e)}")
        finally:
            self.search_btn.setEnabled(True)

    def set_title(self, title):
        self.title_label.setText(title)