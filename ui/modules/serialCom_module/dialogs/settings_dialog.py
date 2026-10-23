# -*- coding: utf-8 -*-
"""_SerialSettingsDialog — 串口模块设置对话框（原 serialCom_module_frame.py 拆出）。"""

from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt
from core.auto_baud_detector import AUTO_BAUD_CONFIG
from ui.modules.serialCom_module.serial_style import (
    SERIAL_SCROLLBAR_STYLE,
    SerialDarkComboBox,
    _DLG_STYLE,
    dialog_line_edit_style,
    log_color_info_style,
    log_color_info_text,
    section_card_style,
    transparent_scroll_area_style,
)
from ui.modules.serialCom_module.widgets import _FramelessChromeDialog
from ui.modules.serialCom_module.controls.mini_slide_toggle import _MiniSlideToggle

class _SerialSettingsDialog(_FramelessChromeDialog):

    def __init__(self, parent=None):
        super().__init__(parent, title="SERIAL SETTINGS", icon_name="settings.svg")
        self._apply_content_style(_DLG_STYLE)
        self.setMinimumSize(720 + 108, 500 + 112)

        root = self._content
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
        self.rx_max_lines_spin.setRange(500, 500000)
        self.rx_max_lines_spin.setValue(10000)
        self.rx_max_lines_spin.setSingleStep(1000)
        self.rx_max_lines_spin.setFixedHeight(26)
        self.rx_max_lines_spin.setToolTip(
            "RX log buffer size (lines). Higher values use more memory; "
            "500000 lines is about 100-300 MB depending on line length."
        )
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
            f"App v{about_info.get('Version', '0.0.0')}  |  "
            f"Module v{about_info.get('Module version', '0.0.0')}  |  "
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
