#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FT Calibration Check 容器页 - 整合 GPADC FT 校准检查与 Output Voltage Check 子项
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PySide6.QtCore import Qt
from ui.theme import Colors, FontSizes
from ui.widgets.config_memory import ConfigMemory
from ui.pages.pmu_test.gpadc_test_ui import GPADCTestUI
from core.ai.ui_action_registry import UIActionSpec
from log_config import get_logger

logger = get_logger(__name__)


class FTCalibCheckUI(QWidget):
    """FT Calibration Check 容器页（子项：GPADC / Output Voltage Check）"""

    _SUBTAB_SUBTITLES = {
        "GPADC": "Two-point FT calibration verification of GPADC (IIC / UART).",
        "Output Voltage Check": "Output voltage calibration check (to be implemented).",
    }

    def __init__(self, n6705c_top=None, instrument_manager=None, ui_action_registry=None):
        super().__init__()
        self._ui_action_registry = ui_action_registry
        self._setup_style()
        self._create_layout(n6705c_top, instrument_manager)
        self._register_ai_ui_actions()

        self._config_memory = ConfigMemory("pmu_test/ft_calib_check", self)
        self._config_memory.bind("current_tab", self.tab_widget)
        self._config_memory.restore()
        self._update_subtitle(self.tab_widget.currentIndex())

    def _setup_style(self):
        # 仅约束容器自身与子项 Tab 栏；子页样式由各自页面 QSS 负责。
        # active/inactive tab 的 padding/border/margin 保持一致（盒模型对齐）。
        self.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background-color: #16181c;
            }
            QTabBar::tab {
                background-color: #16181c;
                color: #8a93a6;
                border: 1px solid #333;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 6px 18px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #0a1733;
                color: #d7dce2;
            }
            QTabBar::tab:hover {
                background-color: #1d2330;
            }
        """)

    def _create_layout(self, n6705c_top, instrument_manager):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 0)
        main_layout.setSpacing(4)

        # 页头（标题 + 副标题）置于子项 Tab 栏上方；嵌入页自身页头在 ft_only 下隐藏
        self._title_label = QLabel("FT Calibration Check")
        self._title_label.setStyleSheet(
            f"font-size: {FontSizes.title}; font-weight: 700; color: #ffffff; border: none;"
        )
        self._subtitle_label = QLabel()
        self._subtitle_label.setStyleSheet(
            f"font-size: {FontSizes.subtitle}; color: {Colors.text_muted}; border: none;"
        )
        main_layout.addWidget(self._title_label)
        main_layout.addWidget(self._subtitle_label)

        self.tab_widget = QTabWidget()
        self.tab_widget.currentChanged.connect(self._update_subtitle)

        # GPADC 子项：复用 GPADCTestUI 的 FT Calibration Check 流程（ft_only 锁定）。
        # ui_action_registry 传 None：避免与 GPADC Test 页重复登记同名 UI 动作，
        # 本页导出动作由 _register_ai_ui_actions 以 pmu_ft_calib 页键单独登记。
        self.gpadc_ui = GPADCTestUI(
            n6705c_top=n6705c_top,
            instrument_manager=instrument_manager,
            ui_action_registry=None,
            ft_only=True,
        )
        self.tab_widget.addTab(self.gpadc_ui, "GPADC")

        self.output_voltage_check_ui = self._build_output_voltage_placeholder()
        self.tab_widget.addTab(self.output_voltage_check_ui, "Output Voltage Check")

        main_layout.addWidget(self.tab_widget, 1)

    def _update_subtitle(self, index):
        self._subtitle_label.setText(
            self._SUBTAB_SUBTITLES.get(self.tab_widget.tabText(index), "")
        )

    def _build_output_voltage_placeholder(self):
        placeholder = QWidget()
        layout = QVBoxLayout(placeholder)
        title = QLabel("Output Voltage Check")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #d7dce2; border: none;")
        hint = QLabel("This check is not implemented yet.")
        hint.setStyleSheet("color: #8a93a6; border: none;")
        layout.addStretch(1)
        layout.addWidget(title, 0, Qt.AlignHCenter)
        layout.addWidget(hint, 0, Qt.AlignHCenter)
        layout.addStretch(2)
        return placeholder

    # ------------------------------------------------------------------
    # PMUTestUI 容器契约：启停按钮 / 运行状态 / 状态与配置透传 GPADC 子项
    # ------------------------------------------------------------------

    @property
    def start_test_btn(self):
        return self.gpadc_ui.start_test_btn

    @property
    def stop_test_btn(self):
        return self.gpadc_ui.stop_test_btn

    @property
    def is_test_running(self):
        return self.gpadc_ui.is_test_running

    def sync_n6705c_from_top(self):
        self.gpadc_ui.sync_n6705c_from_top()

    def sync_chamber_from_manager(self):
        self.gpadc_ui.sync_chamber_from_manager()

    def set_system_status(self, status, is_error=False):
        self.gpadc_ui.set_system_status(status, is_error)

    def update_instrument_info(self, instrument_info):
        self.gpadc_ui.update_instrument_info(instrument_info)

    def get_test_config(self):
        return self.gpadc_ui.get_test_config()

    def update_test_result(self, result):
        self.gpadc_ui.update_test_result(result)

    def clear_results(self):
        self.gpadc_ui.clear_results()

    def get_test_mode(self):
        return self.gpadc_ui.get_test_mode()

    def set_test_mode(self, mode):
        self.gpadc_ui.set_test_mode(mode)

    def get_test_id(self):
        return self.gpadc_ui.get_test_id()

    def set_test_id(self, test_id):
        self.gpadc_ui.set_test_id(test_id)

    def get_capture_pixmap(self):
        if self.tab_widget.currentWidget() is self.gpadc_ui:
            return self.gpadc_ui.get_capture_pixmap()
        return None

    def cleanup_threads(self):
        self.gpadc_ui.cleanup_threads()

    # ------------------------------------------------------------------
    # AI 契约：仅 GPADC 子项激活时透传其能力（Output Voltage Check 待实现）
    # ------------------------------------------------------------------

    def _ai_active_subpage(self):
        if self.tab_widget.currentWidget() is self.gpadc_ui:
            return self.gpadc_ui
        return None

    def ai_capabilities(self) -> set[str]:
        page = self._ai_active_subpage()
        return page.ai_capabilities() if page is not None else set()

    def ai_get_config(self):
        page = self._ai_active_subpage()
        return page.ai_get_config() if page is not None else None

    def ai_apply_config(self, payload):
        page = self._ai_active_subpage()
        if page is None:
            return False, "当前子项不支持配置修改。"
        return page.ai_apply_config(payload)

    def ai_start_test(self):
        page = self._ai_active_subpage()
        if page is None:
            return False, "当前子项不支持启动测试。"
        return page.ai_start_test()

    def ai_stop_test(self):
        page = self._ai_active_subpage()
        if page is None:
            return False, "当前子项不支持停止测试。"
        return page.ai_stop_test()

    def ai_get_result_summary(self):
        page = self._ai_active_subpage()
        return page.ai_get_result_summary() if page is not None else None

    def _register_ai_ui_actions(self):
        registry = self._ui_action_registry
        if registry is None:
            return

        def _run_export() -> tuple[bool, str]:
            try:
                self.gpadc_ui.export_result()
                return True, "导出结果 已执行。"
            except Exception as exc:  # noqa: BLE001
                logger.error("导出结果 执行失败", exc_info=True)
                return False, f"导出结果 执行失败：{exc}"

        registry.register_many([
            UIActionSpec(
                id="pmu_ft_calib.export_result",
                label="导出结果",
                page_key="pmu_ft_calib",
                handler=_run_export,
                risk="low",
                confirm=False,
                enabled_when=lambda: (
                    self.tab_widget.currentWidget() is self.gpadc_ui
                    and self.gpadc_ui._export_data is not None
                ),
                description="导出当前 FT Calibration Check (GPADC) 测试结果为 Excel。需已有测试结果数据。",
            ),
        ])


if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    from ui.standalone import apply_window_icon, resize_and_center_window

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    ft_calib_check_ui = FTCalibCheckUI()
    ft_calib_check_ui.setWindowTitle("FT Calibration Check")
    apply_window_icon(ft_calib_check_ui, "pmu_test")
    resize_and_center_window(ft_calib_check_ui)
    ft_calib_check_ui.show()

    sys.exit(app.exec())
