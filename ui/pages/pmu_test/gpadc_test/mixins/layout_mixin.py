"""GPADCTestUI 布局构建 Mixin（样式 / 控件树 / 布局 / 测试项切换）。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。
类装配见 gpadc_test_ui.py。"""

from ui.widgets.dark_combobox import DarkComboBox
from ui.widgets.wheel_line_edit import WheelLineEdit, HexWheelLineEdit
from ui.styles import SCROLL_AREA_STYLE, START_BTN_STYLE
from ui.widgets.button import update_connect_button_state
from ui.modules.execution_logs_module_frame import ExecutionLogsFrame
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QGridLayout, QSpinBox, QDoubleSpinBox, QFrame, QRadioButton,
    QButtonGroup, QSizePolicy, QStackedWidget, QScrollArea, QTextEdit,
    QProgressBar, QListWidget, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPixmap, QPainter
from lib.i2c.Bes_I2CIO_Interface import I2CSpeedMode
from ui.theme import Colors, FontSizes, Radius, FONT_MONO
from ui.styles import get_page_base_qss
from core.pmu_test.gpadc import ALGORITHM_REGISTRY
from ui.pages.pmu_test.gpadc_multi_temp_panel import MultiChTempPanel

from ui.pages.pmu_test.gpadc_test.toggle_switch import _ToggleSwitch


class _LayoutMixin:
    """布局构建 Mixin（样式 / 控件树 / 布局 / 测试项切换）"""

    def _setup_style(self):
        font = QFont("Segoe UI", 9)
        self.setFont(font)

        page_extra = f"""
            QFrame#page {{
                background-color: {Colors.bg_secondary};
            }}

            QFrame#panel,
            QFrame#chart_panel,
            QFrame#metric_card,
            QFrame#config_inner_panel {{
                background-color: {Colors.bg_card};
                border: 1px solid {Colors.border_primary};
                border-radius: {Radius.card}px;
            }}

            QFrame#left_scroll_content {{
                background: transparent;
                border: none;
            }}

            QWidget#metricsRow {{
                background: transparent;
            }}

            QLabel#title_label {{
                font-size: {FontSizes.title};
                font-weight: 700;
                color: #ffffff;
            }}

            QLabel#subtitle_label {{
                font-size: {FontSizes.subtitle};
                color: {Colors.text_muted};
            }}

            QLabel#section_title {{
                font-size: {FontSizes.body};
                font-weight: 700;
                color: #ffffff;
            }}

            QLabel#muted_label {{
                color: {Colors.text_muted};
                font-size: {FontSizes.caption};
            }}

            QLabel#metric_name {{
                color: {Colors.text_muted};
                font-size: {FontSizes.caption};
                font-weight: 600;
            }}

            QLabel#metric_value_green {{
                color: {Colors.success};
                font-size: 16px;
                font-weight: 700;
            }}

            QLabel#metric_value_blue {{
                color: {Colors.info};
                font-size: 16px;
                font-weight: 700;
            }}

            QLabel#metric_value_yellow {{
                color: {Colors.warning};
                font-size: 16px;
                font-weight: 700;
            }}

            QSpinBox::up-button, QSpinBox::down-button,
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 0px; height: 0px; border: none;
            }}

            QPushButton#connect_btn {{
                background-color: rgba(0, 211, 154, 0.14);
                color: {Colors.success};
                border: 1px solid rgba(0, 211, 154, 0.25);
                font-weight: 600;
            }}

            QPushButton#danger_btn {{
                background-color: rgba(255, 90, 122, 0.14);
                color: #ff6f8e;
                border: 1px solid rgba(255, 90, 122, 0.25);
                font-weight: 600;
            }}
""" + START_BTN_STYLE + f"""
            QPushButton#tool_btn {{
                min-height: 28px;
                border-radius: {Radius.small}px;
                background-color: {Colors.bg_card};
                padding: 4px 10px;
            }}

            QPushButton#tool_btn:checked {{
                background-color: rgba(91, 156, 245, 0.18);
                border: 1px solid {Colors.info};
            }}

            /* 手柄与 log_splitter.qss 同规范：默认透明，悬停/拖拽才显色反馈 */
            QSplitter#recent_curve_splitter::handle {{
                background-color: transparent;
            }}

            QSplitter#recent_curve_splitter::handle:horizontal {{
                width: 2px;
            }}

            QSplitter#recent_curve_splitter::handle:horizontal:hover {{
                background-color: #18284d;
            }}

            QSplitter#recent_curve_splitter::handle:horizontal:pressed {{
                background-color: #5b7cff;
            }}

            QRadioButton {{
                background: transparent;
                color: {Colors.text_secondary};
                spacing: 8px;
            }}

            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
            }}

            QRadioButton::indicator:unchecked {{
                border: 1px solid #4a5e8e;
                border-radius: 7px;
                background: #071126;
            }}

            QRadioButton::indicator:checked {{
                border: 1px solid #4ca8ff;
                border-radius: 7px;
                background: #4ca8ff;
            }}

            QTextEdit {{
                background-color: #050d1e;
                border: 1px solid #0e1e40;
                border-radius: {Radius.small}px;
                color: #8abaff;
                font-size: {FontSizes.caption};
                font-family: {FONT_MONO};
                padding: 6px;
            }}

            QProgressBar {{
                background-color: #152749;
                border: none;
                border-radius: 4px;
                text-align: center;
                color: #b7c8ea;
                min-height: 8px;
                max-height: 8px;
            }}

            QProgressBar::chunk {{
                background-color: {Colors.accent_primary};
                border-radius: 4px;
            }}

            QListWidget#recent_test_list {{
                background-color: #050d1e;
                border: 1px solid #0e1e40;
                border-radius: {Radius.small}px;
                color: #b7c8ea;
                font-size: {FontSizes.caption};
                padding: 4px;
                outline: none;
            }}

            QListWidget#recent_test_list::item {{
                background: transparent;
                border: none;
                padding: 3px 6px;
                border-radius: 4px;
            }}

            QListWidget#recent_test_list::item:hover {{
                background: rgba(91, 156, 245, 0.12);
            }}

            QListWidget#recent_test_list::item:selected {{
                background: rgba(91, 156, 245, 0.22);
            }}

            QLabel#recent_hint_label {{
                color: {Colors.text_muted};
                font-size: {FontSizes.caption};
            }}
        """ + SCROLL_AREA_STYLE
        self.setStyleSheet(get_page_base_qss() + page_extra)

    def _create_metric_card(self, title, value="---", value_object_name="metric_value_green"):
        card = QFrame()
        card.setObjectName("metric_card")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setMinimumHeight(72)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(4)

        name_label = QLabel(title)
        name_label.setObjectName("metric_name")
        name_label.setAlignment(Qt.AlignCenter)

        value_label = QLabel(value)
        value_label.setObjectName(value_object_name)
        value_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(name_label)
        layout.addWidget(value_label)
        return card, value_label

    def _create_layout(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 6, 8, 8)
        root_layout.setSpacing(8)

        self.page = QFrame()
        self.page.setObjectName("page")
        page_layout = QVBoxLayout(self.page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(10)

        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)


        title_label = QLabel("GPADC Automated Test")
        title_label.setObjectName("title_label")
        title_label.setStyleSheet("border: none")

        subtitle_label = QLabel("Evaluate GPADC performance including Linearity, ENOB, and Temperature Drift.")
        subtitle_label.setObjectName("subtitle_label")
        subtitle_label.setStyleSheet("border: none")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        page_layout.addLayout(header_layout)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(8)

        # 左侧滚动区
        left_wrapper = QVBoxLayout()
        left_wrapper.setContentsMargins(0, 0, 0, 0)
        left_wrapper.setSpacing(8)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.left_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.left_scroll.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.left_scroll.setMinimumWidth(310)
        self.left_scroll.setMaximumWidth(310)

        left_content = QFrame()
        left_content.setObjectName("left_scroll_content")
        left_content.setMinimumWidth(300)
        left_content.setMaximumWidth(300)
        left_content.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        left_col = QVBoxLayout(left_content)
        left_col.setContentsMargins(0, 0, 2, 0)
        left_col.setSpacing(12)

        # Test Item (下拉菜单)
        test_item_panel = QFrame()
        test_item_panel.setObjectName("panel")
        test_item_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        test_item_layout = QVBoxLayout(test_item_panel)
        test_item_layout.setContentsMargins(12, 12, 12, 12)
        test_item_layout.setSpacing(8)

        test_item_title = QLabel("Test Item")
        test_item_title.setObjectName("section_title")
        test_item_title.setStyleSheet("border: none")
        test_item_layout.addWidget(test_item_title)

        self.test_item_combo = DarkComboBox(bg="#0a1733", border="#24365e")
        self.test_item_combo.addItem(self.TEST_1000CNT, self.TEST_1000CNT)
        self.test_item_combo.addItem(self.TEST_FORCE_VOLTAGE, self.TEST_FORCE_VOLTAGE)
        self.test_item_combo.addItem(self.TEST_HIGH_LOW_TEMP, self.TEST_HIGH_LOW_TEMP)
        self.test_item_combo.addItem(self.TEST_TEMP_CONSISTENCY, self.TEST_TEMP_CONSISTENCY)
        self.test_item_combo.addItem(self.TEST_MULTI_CH_TEMP, self.TEST_MULTI_CH_TEMP)
        self.test_item_combo.addItem(self.TEST_FT_CALIB_CHECK, self.TEST_FT_CALIB_CHECK)
        test_item_layout.addWidget(self.test_item_combo)
        left_col.addWidget(test_item_panel)

        # Instruments (动态显示)
        self.instruments_panel = QFrame()
        self.instruments_panel.setObjectName("panel")
        self.instruments_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        instruments_layout = QVBoxLayout(self.instruments_panel)
        instruments_layout.setContentsMargins(12, 12, 12, 12)
        instruments_layout.setSpacing(10)

        instruments_title = QLabel("Instruments")
        instruments_title.setObjectName("section_title")
        instruments_title.setStyleSheet("border: none")
        instruments_layout.addWidget(instruments_title)

        self.n6705c_card = QFrame()
        self.n6705c_card.setObjectName("config_inner_panel")
        n6705c_card_layout = QVBoxLayout(self.n6705c_card)
        n6705c_card_layout.setContentsMargins(10, 10, 10, 10)
        n6705c_card_layout.setSpacing(6)
        n6705c_title_row = QHBoxLayout()
        n6705c_title_row.setSpacing(6)
        n6705c_title = QLabel("N6705C")
        n6705c_title.setStyleSheet("color: #c8d8ff; font-size: 11px; font-weight: 600; border: none;")
        n6705c_title_row.addWidget(n6705c_title)
        n6705c_title_row.addStretch()
        n6705c_card_layout.addLayout(n6705c_title_row)
        self.build_n6705c_connection_widgets(n6705c_card_layout, title_row=n6705c_title_row)

        self.n6705c_status = self.system_status_label
        self.n6705c_combo = self.visa_resource_combo
        self.n6705c_search_btn = self.search_btn
        self.n6705c_connect_btn = self.connect_btn
        self.n6705c_disconnect_btn = self.connect_btn

        instruments_layout.addWidget(self.n6705c_card)

        self.chamber_card = QFrame()
        self.chamber_card.setObjectName("config_inner_panel")
        chamber_card_layout = QVBoxLayout(self.chamber_card)
        chamber_card_layout.setContentsMargins(10, 10, 10, 10)
        chamber_card_layout.setSpacing(6)
        chamber_title_row = QHBoxLayout()
        chamber_title_row.setSpacing(6)
        chamber_title = QLabel("Chamber")
        chamber_title.setStyleSheet("color: #c8d8ff; font-size: 11px; font-weight: 600; border: none;")
        chamber_title_row.addWidget(chamber_title)
        chamber_title_row.addStretch()
        chamber_card_layout.addLayout(chamber_title_row)
        self.build_chamber_connection_widgets(chamber_card_layout)
        chamber_card_layout.removeWidget(self.chamber_status_label)
        chamber_title_row.addWidget(self.chamber_status_label)
        instruments_layout.addWidget(self.chamber_card)
        left_col.addWidget(self.instruments_panel)

        # Data Acquisition
        data_panel = QFrame()
        data_panel.setObjectName("panel")
        data_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        data_layout = QVBoxLayout(data_panel)
        data_layout.setContentsMargins(12, 12, 12, 12)
        data_layout.setSpacing(10)

        data_title = QLabel("Data Acquisition")
        data_title.setObjectName("section_title")
        data_layout.addWidget(data_title)

        radio_row = QHBoxLayout()
        radio_row.setSpacing(12)

        self.iic_radio = QRadioButton("I2C")
        self.uart_radio = QRadioButton("UART Log")
        self.iic_radio.setChecked(True)

        self.data_acquisition_group = QButtonGroup()
        self.data_acquisition_group.addButton(self.iic_radio)
        self.data_acquisition_group.addButton(self.uart_radio)

        radio_row.addWidget(self.iic_radio)
        radio_row.addWidget(self.uart_radio)
        radio_row.addStretch()
        data_layout.addLayout(radio_row)

        self.data_stack = QStackedWidget()
        self.data_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.iic_group = QFrame()
        self.iic_group.setObjectName("config_inner_panel")
        iic_layout = QGridLayout(self.iic_group)
        iic_layout.setContentsMargins(10, 10, 10, 10)
        iic_layout.setHorizontalSpacing(6)
        iic_layout.setVerticalSpacing(6)

        iic_layout.addWidget(QLabel("Device Address (Hex)"), 0, 0)
        self.iic_device_address = HexWheelLineEdit("0x17")
        iic_layout.addWidget(self.iic_device_address, 1, 0)

        iic_layout.addWidget(QLabel("Raw Data Register (Hex)"), 2, 0)
        self.iic_data_address = HexWheelLineEdit("0x57")
        iic_layout.addWidget(self.iic_data_address, 3, 0)

        iic_layout.addWidget(QLabel("IIC Width"), 4, 0)
        self.iic_width_combo = DarkComboBox(bg="#0a1733", border="#24365e")
        self.iic_width_combo.addItem("8-bit", 8)
        self.iic_width_combo.addItem("10-bit", 10)
        self.iic_width_combo.addItem("32-bit", 32)
        self.iic_width_combo.setCurrentIndex(1)
        iic_layout.addWidget(self.iic_width_combo, 5, 0)

        iic_layout.addWidget(QLabel("IIC Speed"), 6, 0)
        self.iic_speed_combo = DarkComboBox(bg="#0a1733", border="#24365e")
        self.iic_speed_combo.addItem("20 kHz", int(I2CSpeedMode.SPEED_20K))
        self.iic_speed_combo.addItem("100 kHz", int(I2CSpeedMode.SPEED_100K))
        self.iic_speed_combo.addItem("400 kHz", int(I2CSpeedMode.SPEED_400K))
        self.iic_speed_combo.addItem("750 kHz", int(I2CSpeedMode.SPEED_750K))
        self.iic_speed_combo.setCurrentIndex(1)
        iic_layout.addWidget(self.iic_speed_combo, 7, 0)

        self.uart_group = QFrame()
        self.uart_group.setObjectName("config_inner_panel")
        uart_layout = QVBoxLayout(self.uart_group)
        uart_layout.setContentsMargins(10, 10, 10, 10)
        uart_layout.setSpacing(8)

        self.build_serial_connection_widgets(uart_layout)
        self.bind_serial_signals()

        keyword_label = QLabel("Search Keyword")
        keyword_label.setStyleSheet("border: none;")
        uart_layout.addWidget(keyword_label)
        self.uart_keyword = QLineEdit("raw/volt")
        uart_layout.addWidget(self.uart_keyword)

        self.data_stack.addWidget(self.iic_group)
        self.data_stack.addWidget(self.uart_group)
        data_layout.addWidget(self.data_stack)
        left_col.addWidget(data_panel)

        # Test Parameters
        params_panel = QFrame()
        params_panel.setObjectName("panel")
        params_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        params_layout = QVBoxLayout(params_panel)
        params_layout.setContentsMargins(12, 12, 12, 12)
        params_layout.setSpacing(8)

        self.params_title = QLabel("Test Parameters")
        self.params_title.setObjectName("section_title")
        self.params_title.setStyleSheet("border: none;")
        params_layout.addWidget(self.params_title)

        self.params_mode_label = QLabel("VOLTAGE SWEEP")
        self.params_mode_label.setStyleSheet("color: #7e96bf; font-size: 11px; font-weight: 700; border: none;")
        params_layout.addWidget(self.params_mode_label)

        self.voltage_params_frame = QFrame()
        self.voltage_params_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        voltage_layout = QGridLayout(self.voltage_params_frame)
        voltage_layout.setContentsMargins(0, 0, 0, 0)
        voltage_layout.setHorizontalSpacing(6)
        voltage_layout.setVerticalSpacing(6)

        voltage_layout.addWidget(QLabel("Start (V)"), 0, 0)
        voltage_layout.addWidget(QLabel("End (V)"), 0, 1)
        voltage_layout.addWidget(QLabel("Step (V)"), 0, 2)

        self.voltage_min = QDoubleSpinBox()
        self.voltage_min.setRange(0.0, 5.0)
        self.voltage_min.setValue(4.0)
        self.voltage_min.setSingleStep(0.01)
        self.voltage_min.setDecimals(3)

        self.voltage_max = QDoubleSpinBox()
        self.voltage_max.setRange(0.0, 5.0)
        self.voltage_max.setValue(4.2)
        self.voltage_max.setSingleStep(0.01)
        self.voltage_max.setDecimals(3)

        self.voltage_step = QDoubleSpinBox()
        self.voltage_step.setRange(0.001, 1.0)
        self.voltage_step.setValue(0.05)
        self.voltage_step.setSingleStep(0.010)
        self.voltage_step.setDecimals(3)

        voltage_layout.addWidget(self.voltage_min, 1, 0)
        voltage_layout.addWidget(self.voltage_max, 1, 1)
        voltage_layout.addWidget(self.voltage_step, 1, 2)

        self.temp_params_frame = QFrame()
        self.temp_params_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        temp_layout = QGridLayout(self.temp_params_frame)
        temp_layout.setContentsMargins(0, 0, 0, 0)
        temp_layout.setHorizontalSpacing(6)
        temp_layout.setVerticalSpacing(6)

        temp_layout.addWidget(QLabel("Start (°C)"), 0, 0)
        temp_layout.addWidget(QLabel("End (°C)"), 0, 1)
        temp_layout.addWidget(QLabel("Step (°C)"), 0, 2)

        self.temp_min = QDoubleSpinBox()
        self.temp_min.setRange(-40.0, 125.0)
        self.temp_min.setValue(-40.0)
        self.temp_min.setSingleStep(1.0)
        self.temp_min.setDecimals(1)

        self.temp_max = QDoubleSpinBox()
        self.temp_max.setRange(-40.0, 125.0)
        self.temp_max.setValue(125.0)
        self.temp_max.setSingleStep(1.0)
        self.temp_max.setDecimals(1)

        self.temp_step = QDoubleSpinBox()
        self.temp_step.setRange(0.1, 50.0)
        self.temp_step.setValue(5)
        self.temp_step.setSingleStep(0.1)
        self.temp_step.setDecimals(2)

        temp_layout.addWidget(self.temp_min, 1, 0)
        temp_layout.addWidget(self.temp_max, 1, 1)
        temp_layout.addWidget(self.temp_step, 1, 2)

        temp_layout.addWidget(QLabel("Soak Time (s)"), 2, 0)
        self.soak_time = QSpinBox()
        self.soak_time.setRange(0, 3600)
        self.soak_time.setValue(180)
        self.soak_time.setSingleStep(30)
        temp_layout.addWidget(self.soak_time, 3, 0)

        params_layout.addWidget(self.voltage_params_frame)
        params_layout.addWidget(self.temp_params_frame)

        # 校准参数：默认留空 = 自动取 1/4、3/4 扫描点；两格都填写时作为手动校准两点
        self.calib_params_frame = QFrame()
        self.calib_params_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        calib_layout = QGridLayout(self.calib_params_frame)
        calib_layout.setContentsMargins(0, 0, 0, 0)
        calib_layout.setHorizontalSpacing(6)
        calib_layout.setVerticalSpacing(6)

        self.calib_low_label = QLabel("Calib Low (V)")
        self.calib_high_label = QLabel("Calib High (V)")
        calib_layout.addWidget(self.calib_low_label, 0, 0)
        calib_layout.addWidget(self.calib_high_label, 0, 1)

        self.calib_low = WheelLineEdit()
        self.calib_low.setPlaceholderText("Auto")
        self.calib_high = WheelLineEdit()
        self.calib_high.setPlaceholderText("Auto")
        calib_layout.addWidget(self.calib_low, 1, 0)
        calib_layout.addWidget(self.calib_high, 1, 1)

        params_layout.addWidget(self.calib_params_frame)

        # FT Calibration Check 参数：两个 FT 校准点（电压 + 校准码）与判定阈值
        # 仅 TEST_FT_CALIB_CHECK 测试项可见
        self.ft_params_frame = QFrame()
        self.ft_params_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        ft_layout = QGridLayout(self.ft_params_frame)
        ft_layout.setContentsMargins(0, 0, 0, 0)
        ft_layout.setHorizontalSpacing(6)
        ft_layout.setVerticalSpacing(6)

        ft_layout.addWidget(QLabel("Calib Point 1 (V)"), 0, 0)
        ft_layout.addWidget(QLabel("Calib Raw 1 (LSB)"), 0, 1)
        self.ft_calib_v1 = WheelLineEdit("1.0")
        self.ft_calib_c1 = WheelLineEdit("3277", wheel_step=1)
        _raw_tip = ("支持十进制 / 0x 十六进制（如 0x13F），"
                    "及 base+offset 自动求值（如 0x13F+2000 → 2319）")
        self.ft_calib_c1.setToolTip(_raw_tip)
        ft_layout.addWidget(self.ft_calib_v1, 1, 0)
        ft_layout.addWidget(self.ft_calib_c1, 1, 1)

        ft_layout.addWidget(QLabel("Calib Point 2 (V)"), 2, 0)
        ft_layout.addWidget(QLabel("Calib Raw 2 (LSB)"), 2, 1)
        self.ft_calib_v2 = WheelLineEdit("3.0")
        self.ft_calib_c2 = WheelLineEdit("9830", wheel_step=1)
        self.ft_calib_c2.setToolTip(_raw_tip)
        ft_layout.addWidget(self.ft_calib_v2, 3, 0)
        ft_layout.addWidget(self.ft_calib_c2, 3, 1)

        ft_layout.addWidget(QLabel("Raw Tol (±LSB)"), 4, 0)
        ft_layout.addWidget(QLabel("Error Limit (±mV)"), 4, 1)
        self.ft_raw_tol = QDoubleSpinBox()
        self.ft_raw_tol.setRange(0.0, 1000.0)
        self.ft_raw_tol.setValue(10.0)
        self.ft_raw_tol.setSingleStep(1.0)
        self.ft_raw_tol.setDecimals(1)
        self.ft_err_limit = QDoubleSpinBox()
        self.ft_err_limit.setRange(0.0, 10000.0)
        self.ft_err_limit.setValue(10.0)
        self.ft_err_limit.setSingleStep(1.0)
        self.ft_err_limit.setDecimals(1)
        ft_layout.addWidget(self.ft_raw_tol, 5, 0)
        ft_layout.addWidget(self.ft_err_limit, 5, 1)

        ft_layout.addWidget(QLabel("Divider Ratio (×)"), 6, 0)
        self.ft_divider_ratio = QDoubleSpinBox()
        self.ft_divider_ratio.setRange(0.0001, 1000.0)
        self.ft_divider_ratio.setValue(1.0)
        self.ft_divider_ratio.setSingleStep(0.01)
        self.ft_divider_ratio.setDecimals(4)
        self.ft_divider_ratio.setToolTip(
            "外部分压比 = 源设定电压 / DUT 引脚电压（如外部四分压填 4），默认 1（无分压）。\n"
            "扫压 Start/End/Step 为源设定电压（不缩放输出）；\n"
            "DUT 侧得出的校准电压按 × 比值还原到源域后与设定值比对评估；\n"
            "校准点电压为 DUT 引脚电压（FT 标称值），IIC 确认时源输出 = 点电压 × 比值。"
        )
        ft_layout.addWidget(self.ft_divider_ratio, 7, 0)

        params_layout.addWidget(self.ft_params_frame)
        self.ft_params_frame.hide()

        self.sample_count_label = QLabel("Sample Count")
        self.sample_count_label.setObjectName("muted_label")
        params_layout.addWidget(self.sample_count_label)

        self.sample_count = QSpinBox()
        self.sample_count.setRange(1, 100000)
        self.sample_count.setValue(1000)
        self.sample_count.setSingleStep(100)
        params_layout.addWidget(self.sample_count)

        self.voltage_channel_label = QLabel("Voltage Channel")
        self.voltage_channel_label.setObjectName("muted_label")
        params_layout.addWidget(self.voltage_channel_label)

        self.voltage_channel = DarkComboBox(bg="#0a1733", border="#24365e")
        for ch in range(1, 5):
            self.voltage_channel.addItem(f"Channel {ch}", ch)
        self.voltage_channel.setCurrentIndex(3)
        params_layout.addWidget(self.voltage_channel)

        # 采样算法：默认 None（原始数据，与既有流程一致）；参数控件按注册表动态生成
        self.algo_title = QLabel("Algorithm")
        self.algo_title.setObjectName("muted_label")
        params_layout.addWidget(self.algo_title)

        self.algorithm_combo = DarkComboBox(bg="#0a1733", border="#24365e")
        self.algorithm_combo.addItem("None (原始数据)", "")
        for _algo_id, _algo_spec in ALGORITHM_REGISTRY.items():
            self.algorithm_combo.addItem(_algo_spec['name'], _algo_id)
        self.algorithm_combo.setToolTip("采样数据处理算法；None = 不处理，与原始测试流程一致")
        params_layout.addWidget(self.algorithm_combo)

        self.algo_params_frame = QFrame()
        self.algo_params_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        self.algo_params_layout = QGridLayout(self.algo_params_frame)
        self.algo_params_layout.setContentsMargins(0, 0, 0, 0)
        self.algo_params_layout.setHorizontalSpacing(6)
        self.algo_params_layout.setVerticalSpacing(6)
        params_layout.addWidget(self.algo_params_frame)
        self._algo_param_widgets: dict[str, QDoubleSpinBox] = {}
        self._rebuild_algorithm_params()
        self.algorithm_combo.currentIndexChanged.connect(self._on_algorithm_changed)

        # 离群样本筛选：剔除与平均值正/负向偏差超过阈值的样本（FT 测试项不适用，隐藏）
        self.outlier_filter_title = QLabel("Outlier Filter")
        self.outlier_filter_title.setObjectName("muted_label")
        params_layout.addWidget(self.outlier_filter_title)

        self.outlier_filter_frame = QFrame()
        self.outlier_filter_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        filter_layout = QGridLayout(self.outlier_filter_frame)
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setHorizontalSpacing(6)
        filter_layout.setVerticalSpacing(6)

        filter_enable_label = QLabel("Enable")
        filter_enable_label.setObjectName("muted_label")
        filter_layout.addWidget(filter_enable_label, 0, 0)
        self.outlier_filter_switch = _ToggleSwitch(checked=False)
        self.outlier_filter_switch.setToolTip(
            "启用后剔除与平均值正/负向偏差超过阈值的样本（采样算法之前应用）"
        )
        filter_layout.addWidget(self.outlier_filter_switch, 0, 1, Qt.AlignRight)

        filter_layout.addWidget(QLabel("Max Positive Offset (LSB)"), 1, 0)
        filter_layout.addWidget(QLabel("Max Negative Offset (LSB)"), 1, 1)
        self.outlier_pos_offset = QDoubleSpinBox()
        self.outlier_pos_offset.setRange(0.0, 100000.0)
        self.outlier_pos_offset.setValue(10.0)
        self.outlier_pos_offset.setSingleStep(1.0)
        self.outlier_pos_offset.setDecimals(1)
        self.outlier_neg_offset = QDoubleSpinBox()
        self.outlier_neg_offset.setRange(0.0, 100000.0)
        self.outlier_neg_offset.setValue(10.0)
        self.outlier_neg_offset.setSingleStep(1.0)
        self.outlier_neg_offset.setDecimals(1)
        filter_layout.addWidget(self.outlier_pos_offset, 2, 0)
        filter_layout.addWidget(self.outlier_neg_offset, 2, 1)
        params_layout.addWidget(self.outlier_filter_frame)

        self.outlier_filter_switch.toggled.connect(self._on_outlier_filter_toggled)
        self._on_outlier_filter_toggled(False)

        self.temp_hint_label = QLabel("Connect chamber to enable temperature testing.")
        self.temp_hint_label.setStyleSheet("color: #ff5a7a; font-size: 11px;")
        self.temp_hint_label.setWordWrap(True)
        params_layout.addWidget(self.temp_hint_label)

        left_col.addWidget(params_panel)

        # 多通道高低温测试配置（仅 Multi-Ch Temp Test 测试项可见）
        self.multi_ch_panel = MultiChTempPanel(self)
        self.multi_ch_panel.save_requested.connect(self._on_save_multi_ch_config)
        self.multi_ch_panel.load_requested.connect(self._on_load_multi_ch_config)
        self.multi_ch_panel.hide()
        left_col.addWidget(self.multi_ch_panel)

        left_col.addStretch()

        self.left_scroll.setWidget(left_content)
        left_wrapper.addWidget(self.left_scroll, 1)

        self.start_test_btn = QPushButton("▶ START TEST")
        self.start_test_btn.setObjectName("primaryStartBtn")
        # 宽度与上方面板可见宽对齐（左列内容宽 - 列右边距），防止长文本撑开左列
        self.start_test_btn.setMaximumWidth(
            left_content.maximumWidth() - left_col.contentsMargins().right()
        )
        left_wrapper.addWidget(self.start_test_btn)

        self.stop_test_btn = QPushButton("■")
        self.stop_test_btn.setObjectName("stopBtn")
        self.stop_test_btn.setEnabled(False)
        self.stop_test_btn.hide()

        # 右侧
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        # 性能指标卡行：包进独立容器，供一键截图（get_capture_pixmap）整行抓取
        metrics_row = QWidget()
        metrics_row.setObjectName("metricsRow")
        metrics_row.setAttribute(Qt.WA_StyledBackground, True)
        metrics_layout = QHBoxLayout(metrics_row)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(8)
        self.metrics_row = metrics_row

        inl_card, self.inl_value = self._create_metric_card("INL", "---", "metric_value_green")
        dnl_card, self.dnl_value = self._create_metric_card("DNL", "---", "metric_value_green")
        enob_card, self.enob_value = self._create_metric_card("ENOB", "---", "metric_value_blue")
        offset_card, self.offset_error_value = self._create_metric_card("OFFSET ERR", "---", "metric_value_yellow")
        gain_card, self.gain_error_value = self._create_metric_card("GAIN ERR", "---", "metric_value_yellow")
        
        # 添加1000CNT TEST的指标卡片
        avg_card, self.avg_value = self._create_metric_card("AVG", "---", "metric_value_green")
        min_card, self.min_value = self._create_metric_card("MIN", "---", "metric_value_blue")
        max_card, self.max_value = self._create_metric_card("MAX", "---", "metric_value_yellow")
        std_card, self.std_value = self._create_metric_card("STD (code)", "---", "metric_value_blue")
        pp_card, self.pp_value = self._create_metric_card("P-P NOISE (code)", "---", "metric_value_yellow")
        samples_card, self.samples_value = self._create_metric_card("SAMPLES", "---", "metric_value_green")

        # 按测试项分组显隐：1000CNT 展示详细统计卡组，其余测试项展示线性度卡组
        self._cnt_cards = [avg_card, min_card, max_card, std_card, pp_card, samples_card]
        self._fv_cards = [inl_card, dnl_card, enob_card, offset_card, gain_card]

        # FT Calibration Check 指标卡组（P1/P2 偏差仅 IIC 方式有值，CONS 仅 UART 方式有值）
        ft_p1_card, self.ft_p1_value = self._create_metric_card("P1 DEV (LSB)", "---", "metric_value_green")
        ft_p2_card, self.ft_p2_value = self._create_metric_card("P2 DEV (LSB)", "---", "metric_value_green")
        ft_max_card, self.ft_max_err_value = self._create_metric_card("MAX ERR (mV)", "---", "metric_value_yellow")
        ft_rms_card, self.ft_rms_err_value = self._create_metric_card("RMS ERR (mV)", "---", "metric_value_blue")
        ft_cons_card, self.ft_cons_value = self._create_metric_card("CONS MAX (mV)", "---", "metric_value_yellow")
        ft_result_card, self.ft_result_value = self._create_metric_card("RESULT", "---", "metric_value_blue")
        self._ft_cards = [ft_p1_card, ft_p2_card, ft_max_card, ft_rms_card, ft_cons_card, ft_result_card]

        self.linearity_value = QLabel("---")
        self.linearity_value.hide()

        metrics_layout.addWidget(inl_card)
        metrics_layout.addWidget(dnl_card)
        metrics_layout.addWidget(enob_card)
        metrics_layout.addWidget(offset_card)
        metrics_layout.addWidget(gain_card)
        metrics_layout.addWidget(avg_card)
        metrics_layout.addWidget(min_card)
        metrics_layout.addWidget(max_card)
        metrics_layout.addWidget(std_card)
        metrics_layout.addWidget(pp_card)
        metrics_layout.addWidget(samples_card)
        for ft_card in self._ft_cards:
            metrics_layout.addWidget(ft_card)

        right_col.addWidget(metrics_row)

        chart_panel = QFrame()
        chart_panel.setObjectName("chart_panel")
        chart_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.chart_panel = chart_panel

        chart_layout = QVBoxLayout(chart_panel)
        chart_layout.setContentsMargins(14, 14, 14, 14)
        chart_layout.setSpacing(10)

        chart_top = QHBoxLayout()
        chart_title = QLabel("ADC Transfer Curve")
        chart_title.setObjectName("section_title")
        chart_title.setStyleSheet("border: none;")
        self.chart_title = chart_title

        self.export_result_btn = QPushButton("Export Result")
        self.export_result_btn.setObjectName("tool_btn")

        # Recent 管理栏折叠/展开开关（面板在 Curve 右侧，默认折叠）
        self.toggle_recent_btn = QPushButton("Recent ▶")
        self.toggle_recent_btn.setObjectName("tool_btn")
        self.toggle_recent_btn.setCheckable(True)
        self.toggle_recent_btn.setChecked(False)
        self.toggle_recent_btn.setToolTip("显示/隐藏最近测试管理栏")

        chart_top.addWidget(chart_title)
        chart_top.addStretch()
        chart_top.addWidget(self.toggle_recent_btn)
        chart_top.addWidget(self.export_result_btn)
        chart_layout.addLayout(chart_top)

        self.chart_placeholder = QFrame()
        self.chart_placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.chart_placeholder.setMinimumHeight(200)
        self.chart_placeholder.setStyleSheet("""
            QFrame {
                background-color: #0a1735;
                border: none;
                border-radius: 8px;
            }
        """)
        # 图表区右键：弹 Curve View 显示项菜单（空图状态下也可用）
        self.chart_placeholder.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chart_placeholder.customContextMenuRequested.connect(self._show_curve_view_menu)
        self._build_default_chart_placeholder()

        chart_layout.addWidget(self.chart_placeholder, 1)

        right_splitter, self.execution_logs = ExecutionLogsFrame.wrap_with(
            chart_panel, title="TEST LOG", show_progress=True, stretch=(3, 2)
        )
        self.log_text = self.execution_logs.log_edit
        self.progress_bar = self.execution_logs.progress_bar
        self.progress_text_label = self.execution_logs.progress_text_label
        self.clear_log_btn = self.execution_logs.clear_log_btn

        # Curve 右侧可折叠的最近测试管理栏：与图表区水平分栏
        self.recent_curve_splitter = QSplitter(Qt.Horizontal)
        self.recent_curve_splitter.setObjectName("recent_curve_splitter")
        self.recent_curve_splitter.addWidget(right_splitter)
        self.recent_curve_splitter.addWidget(self._create_recent_tests_panel())
        self.recent_curve_splitter.setStretchFactor(0, 1)
        self.recent_curve_splitter.setStretchFactor(1, 0)
        self.recent_curve_splitter.setSizes([1200, 260])
        # 默认折叠 Recent 管理栏（展开宽度沿用 _recent_panel_sizes 默认值）
        self.recent_curve_splitter.widget(1).setVisible(False)

        right_col.addWidget(self.recent_curve_splitter, 1)

        self.export_params_btn = QPushButton("Export Parameters")
        self.export_params_btn.hide()

        self.save_config_btn = QPushButton("Save Config")
        self.load_config_btn = QPushButton("Load Config")
        self.save_config_btn.hide()
        self.load_config_btn.hide()

        body_layout.addLayout(left_wrapper, 0)
        body_layout.addLayout(right_col, 1)

        page_layout.addLayout(body_layout, 1)
        root_layout.addWidget(self.page, 1)

    def get_capture_pixmap(self):
        """一键截图目标：性能指标卡行 + 图表卡片纵向合成（不含日志区与 Recent 管理栏）。

        MainWindow 顶栏截图按钮的最高优先级钩子；返回 None 时降级为整页截图。
        """
        pieces = []
        for widget in (self.metrics_row, self.chart_panel):
            if not isinstance(widget, QWidget) or not widget.isVisibleTo(self):
                continue
            pm = widget.grab()
            if not pm.isNull():
                pieces.append(pm)
        if not pieces:
            return None
        if len(pieces) == 1:
            return pieces[0]

        gap = 12  # 与 right_col 行间距一致
        width = max(pm.width() for pm in pieces)
        height = sum(pm.height() for pm in pieces) + gap * (len(pieces) - 1)
        merged = QPixmap(width, height)
        merged.fill(QColor(Colors.bg_secondary))
        painter = QPainter(merged)
        try:
            y = 0
            for pm in pieces:
                painter.drawPixmap(0, y, pm)
                y += pm.height() + gap
        finally:
            painter.end()
        return merged

    def _init_ui_elements(self):
        self.current_test_item = self.TEST_1000CNT

        self.iic_radio.toggled.connect(self._update_data_acquisition_ui)
        self.uart_radio.toggled.connect(self._update_data_acquisition_ui)

        self.test_item_combo.currentIndexChanged.connect(self._on_test_item_changed)

        self.bind_n6705c_signals()
        self.bind_chamber_signals()
        self.chamber_connection_changed.connect(self._update_temp_hint)
        self.serial_data_received.connect(self._on_uart_rx_data)

        self.start_test_btn.clicked.connect(self._on_start_or_stop)
        self.stop_test_btn.clicked.connect(self._stop_test)
        self.export_result_btn.clicked.connect(self.export_result)

        self.compare_recent_btn.clicked.connect(self._on_compare_recent_tests)
        self.load_recent_btn.clicked.connect(self._on_load_recent_test)
        self.clear_recent_btn.clicked.connect(self._on_clear_recent_tests)
        self.recent_test_list.itemDoubleClicked.connect(self._on_recent_item_double_clicked)
        self.recent_test_list.itemSelectionChanged.connect(self._on_recent_selection_changed)
        self.recent_test_list.customContextMenuRequested.connect(self._show_recent_item_menu)

        self.toggle_recent_btn.toggled.connect(self._on_toggle_recent_panel)
        for btn in (self.show_mean_btn, self.show_band_btn, self.show_error_btn):
            btn.toggled.connect(self._on_curve_view_changed)

        self._update_data_acquisition_ui()
        self._set_test_item(self.TEST_1000CNT)

    def _on_test_item_changed(self, index):
        test_item = self.test_item_combo.currentData()
        if test_item:
            self._set_test_item(test_item)

    def _set_status_label(self, label, text, status_type="err"):
        if status_type == "ok":
            label.setStyleSheet("color: #00d39a; font-weight: 600; border: none;")
        elif status_type == "warn":
            label.setStyleSheet("color: #ffb84d; font-weight: 600; border: none;")
        elif status_type == "warn":
            label.setStyleSheet("color: #ffb84d; font-weight: 600; border: none;")
        else:
            label.setStyleSheet("color: #ff5a7a; font-weight: 600; border: none;")
        label.setText(text)

    def _update_data_acquisition_ui(self):
        if self.iic_radio.isChecked():
            self.data_stack.setCurrentWidget(self.iic_group)
        else:
            self.data_stack.setCurrentWidget(self.uart_group)

    def _set_test_item(self, test_item):
        self.current_test_item = test_item

        required = self.INSTRUMENT_MAP.get(test_item, [])
        has_instruments = len(required) > 0
        self.instruments_panel.setVisible(has_instruments)
        self.n6705c_card.setVisible("n6705c" in required)
        self.chamber_card.setVisible("chamber" in required)

        # 1000CNT 不再隐藏图表面板：改用于展示原始数据相对 AVG 的分布图，指标区改显详细统计卡组
        is_cnt_test = test_item == self.TEST_1000CNT
        is_ft_test = test_item == self.TEST_FT_CALIB_CHECK
        if is_cnt_test:
            self.chart_title.setText("Raw Data Distribution")
        elif is_ft_test:
            self.chart_title.setText("FT Calibration Curve")
        else:
            self.chart_title.setText("ADC Transfer Curve")
        for card in self._cnt_cards:
            card.setVisible(is_cnt_test)
        for card in self._fv_cards:
            card.setVisible(not is_cnt_test and not is_ft_test)
        for card in self._ft_cards:
            card.setVisible(is_ft_test)

        if test_item == self.TEST_1000CNT:
            self.params_mode_label.setText("1000 COUNT TEST")
            self.voltage_params_frame.hide()
            self.temp_params_frame.hide()
            self.voltage_channel_label.hide()
            self.voltage_channel.hide()
            self.start_test_btn.setText("▶ START TEST")
            self._start_btn_text = "▶ START TEST"
        elif test_item == self.TEST_FORCE_VOLTAGE:
            self.params_mode_label.setText("VOLTAGE SWEEP")
            self.voltage_params_frame.show()
            self.temp_params_frame.hide()
            self.voltage_channel_label.show()
            self.voltage_channel.show()
            self.start_test_btn.setText("▶ START TEST")
            self._start_btn_text = "▶ START TEST"
        elif test_item == self.TEST_FT_CALIB_CHECK:
            self.params_mode_label.setText("FT CALIBRATION CHECK")
            self.voltage_params_frame.show()
            self.temp_params_frame.hide()
            self.voltage_channel_label.show()
            self.voltage_channel.show()
            self.start_test_btn.setText("▶ START TEST")
            self._start_btn_text = "▶ START TEST"
        elif test_item == self.TEST_HIGH_LOW_TEMP:
            self.params_mode_label.setText("TEMPERATURE SWEEP")
            self.voltage_params_frame.hide()
            self.temp_params_frame.show()
            self.voltage_channel_label.show()
            self.voltage_channel.show()
            self.start_test_btn.setText("▶ START TEST")
            self._start_btn_text = "▶ START TEST"
        elif test_item == self.TEST_MULTI_CH_TEMP:
            self.params_mode_label.setText("MULTI-CH TEMPERATURE")
            self.voltage_params_frame.hide()
            self.temp_params_frame.show()
            # 扫压参数逐通道配置，页面级 Voltage Channel 隐藏
            self.voltage_channel_label.hide()
            self.voltage_channel.hide()
            self.start_test_btn.setText("▶ START TEST")
            self._start_btn_text = "▶ START TEST"
        else:
            self.params_mode_label.setText("VOLTAGE + TEMPERATURE")
            self.voltage_params_frame.show()
            self.temp_params_frame.show()
            self.voltage_channel_label.show()
            self.voltage_channel.show()
            self.start_test_btn.setText("▶ START TEST")
            self._start_btn_text = "▶ START TEST"

        # 校准点仅在线性度类测试项生效；温度扫描时 x 轴为温度，单位随动
        # FT Calibration Check 用独立 ft_params_frame（两点四值必填 + 判定阈值）
        self.calib_params_frame.setVisible(not is_cnt_test and not is_ft_test)
        self.ft_params_frame.setVisible(is_ft_test)

        # FT Calibration Check 不应用采样算法与离群筛选（保 raw↔volt 配对）：两区整体隐藏
        # （其余测试项按注册表恢复参数区可见性，不重建控件以保留已调参数值）
        self.algo_title.setVisible(not is_ft_test)
        self.algorithm_combo.setVisible(not is_ft_test)
        self.outlier_filter_title.setVisible(not is_ft_test)
        self.outlier_filter_frame.setVisible(not is_ft_test)
        if is_ft_test:
            self.algo_params_frame.hide()
        else:
            self.algo_params_frame.setVisible(
                ALGORITHM_REGISTRY.get(self.algorithm_combo.currentData()) is not None
            )
        calib_unit = "°C" if test_item == self.TEST_HIGH_LOW_TEMP else "V"
        self.calib_low_label.setText(f"Calib Low ({calib_unit})")
        self.calib_high_label.setText(f"Calib High ({calib_unit})")

        # 多通道高低温测试的通道配置面板
        self.multi_ch_panel.setVisible(test_item == self.TEST_MULTI_CH_TEMP)

        self._update_temp_hint()

    def _update_temp_hint(self):
        """温度类测试项且温箱未连接时才提示连接温箱"""
        needs_chamber = "chamber" in self.INSTRUMENT_MAP.get(self.current_test_item, [])
        self.temp_hint_label.setVisible(needs_chamber and not self.is_chamber_connected)

    def _set_btn_connected(self, btn):
        update_connect_button_state(btn, connected=True)
        btn.setEnabled(True)

    def _set_btn_disconnected(self, btn):
        update_connect_button_state(btn, connected=False)
        btn.setEnabled(True)

    def _set_ui_enabled(self, enabled):
        widgets = [
            self.n6705c_combo, self.n6705c_search_btn, self.n6705c_connect_btn,
            self.chamber_port_combo, self.chamber_search_btn, self.chamber_connect_btn,
            self.serial_combo, self.serial_search_btn, self.serial_connect_btn, self.uart_keyword,
            self.iic_radio, self.uart_radio,
            self.iic_device_address, self.iic_data_address, self.iic_width_combo,
            self.iic_speed_combo,
            self.test_item_combo,
            self.voltage_channel,
            self.voltage_min, self.voltage_max, self.voltage_step,
            self.temp_min, self.temp_max, self.temp_step,
            self.soak_time, self.sample_count,
            self.calib_low, self.calib_high,
            self.ft_calib_v1, self.ft_calib_c1,
            self.ft_calib_v2, self.ft_calib_c2,
            self.ft_raw_tol, self.ft_err_limit,
            self.ft_divider_ratio,
            self.algorithm_combo,
            self.outlier_filter_switch,
            self.naming_chip_edit, self.naming_channel_edit, self.naming_case_edit,
            self.recent_test_list, self.compare_recent_btn,
            self.load_recent_btn, self.clear_recent_btn,
            self.multi_ch_panel,
        ]
        for widget in widgets:
            widget.setEnabled(enabled)
        for spin in self._algo_param_widgets.values():
            spin.setEnabled(enabled)
        # 离群筛选偏移输入的可用性始终跟随开关（恢复可用时不得越过开关状态）
        self.outlier_pos_offset.setEnabled(enabled and self.outlier_filter_switch.isChecked())
        self.outlier_neg_offset.setEnabled(enabled and self.outlier_filter_switch.isChecked())

    def _rebuild_algorithm_params(self):
        """按当前选中算法重建参数行（参数元信息来自 ALGORITHM_REGISTRY）。"""
        while self.algo_params_layout.count():
            item = self.algo_params_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._algo_param_widgets = {}
        algo_id = self.algorithm_combo.currentData()
        spec = ALGORITHM_REGISTRY.get(algo_id) if algo_id else None
        if spec is None:
            self.algo_params_frame.setVisible(False)
            return
        for row, (key, p) in enumerate(spec.get('params', {}).items()):
            label = QLabel(p.get('label', key))
            label.setObjectName("muted_label")
            self.algo_params_layout.addWidget(label, row * 2, 0)
            spin = QDoubleSpinBox()
            spin.setRange(p.get('min', 0.0), p.get('max', 100.0))
            spin.setValue(p.get('default', 0.0))
            spin.setSingleStep(p.get('step', 1.0))
            spin.setDecimals(p.get('decimals', 0))
            self.algo_params_layout.addWidget(spin, row * 2 + 1, 0)
            self._algo_param_widgets[key] = spin
        self.algo_params_frame.setVisible(True)

    def _on_outlier_filter_toggled(self, checked: bool):
        """离群筛选开关联动正/负偏移输入可用性。"""
        self.outlier_pos_offset.setEnabled(checked)
        self.outlier_neg_offset.setEnabled(checked)

    def _on_algorithm_changed(self):
        """切换算法后重建参数区并更新算法说明提示。"""
        self._rebuild_algorithm_params()
        algo_id = self.algorithm_combo.currentData()
        spec = ALGORITHM_REGISTRY.get(algo_id) if algo_id else None
        self.algorithm_combo.setToolTip(
            spec['desc'] if spec else "采样数据处理算法；None = 不处理，与原始测试流程一致"
        )
