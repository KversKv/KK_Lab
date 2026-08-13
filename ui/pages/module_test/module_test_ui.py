#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Test 顶层容器（CommandBar + QStackedWidget 切换 LDO/DCDC）。

P3 重构：隐藏 tabBar 的 QTabWidget → ``QStackedWidget`` + 顶部 ``CommandBar``
（Segmented 显式呈现当前模块）。``set_current_test()`` 外部驱动能力保留
（nav_controller 调用不变），切换模块时 CommandBar 重绑当前子页
（连接状态镜像 / 配置名 / 运行态联动）。

契约（不可破坏）：构造透传 n6705c_top / mso64b_top / chamber_ui /
instrument_manager / ui_action_registry；公共 API 同名同签名。
"""
from __future__ import annotations

if __name__ == "__main__" and __package__ in (None, ""):
    # 直跑本文件时把项目根注入 sys.path，使 log_config 等根级模块可导入；
    # 作为模块被 import 时本块不执行，不影响正常分层。
    import os
    import sys

    sys.path.insert(
        0,
        os.path.dirname(
            os.path.dirname(
                os.path.dirname(
                    os.path.dirname(os.path.abspath(__file__))
                )
            )
        ),
    )

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget
from log_config import get_logger

from ui.pages.module_test._sections.command_bar import CommandBar
from ui.pages.module_test.dcdc_test_ui import DCDCTestUI
from ui.pages.module_test.ldo_test_ui import LDOTestUI
from ui.theme import apply_qss

logger = get_logger(__name__)


class ModuleTestUI(QWidget):
    """Module Test 顶层容器。"""

    TEST_TAB_MAP = {"ldo": 0, "dcdc": 1}

    def __init__(self, n6705c_top=None, mso64b_top=None, chamber_ui=None,
                 instrument_manager=None, ui_action_registry=None):
        super().__init__()
        self._n6705c_top = n6705c_top
        self._mso64b_top = mso64b_top
        self._chamber_ui = chamber_ui
        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry

        self._config_prompted: set[str] = set()
        apply_qss(self, "controls")
        self._create_layout()

        # 首次进入模块测试时，对当前子页提示一次加载配置（非模态 Banner）
        QTimer.singleShot(0, self._auto_prompt_current_config)

    # ------------------------------------------------------------------ 布局
    def _create_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.command_bar = CommandBar((("ldo", "LDO"), ("dcdc", "DCDC")))
        self.command_bar.moduleChanged.connect(self.set_current_test)
        self.command_bar.openConfigRequested.connect(
            lambda: self._call_current("_on_open_config"))
        self.command_bar.saveConfigRequested.connect(
            lambda: self._call_current("_on_save_config"))
        self.command_bar.saveAsConfigRequested.connect(
            lambda: self._call_current("_on_save_config_as"))
        self.command_bar.connectionSettingsRequested.connect(
            self._on_connection_settings)
        layout.addWidget(self.command_bar)

        self.stack = QStackedWidget()
        self.ldo_test_ui = LDOTestUI(
            n6705c_top=self._n6705c_top,
            mso64b_top=self._mso64b_top,
            chamber_ui=self._chamber_ui,
            instrument_manager=self._instrument_manager,
            ui_action_registry=self._ui_action_registry,
        )
        self.dcdc_test_ui = DCDCTestUI(
            n6705c_top=self._n6705c_top,
            mso64b_top=self._mso64b_top,
            chamber_ui=self._chamber_ui,
            instrument_manager=self._instrument_manager,
            ui_action_registry=self._ui_action_registry,
        )
        self.stack.addWidget(self.ldo_test_ui)   # index 0 = ldo
        self.stack.addWidget(self.dcdc_test_ui)  # index 1 = dcdc
        layout.addWidget(self.stack, 1)

        for sub in (self.ldo_test_ui, self.dcdc_test_ui):
            sub.runStateChanged.connect(self._on_sub_run_state)
            sub.configNameChanged.connect(self._on_sub_config_name_changed)

        self.stack.currentChanged.connect(self._on_tab_changed)
        self.command_bar.bind_subpage(self.ldo_test_ui)

    # ------------------------------------------------------------------ 切换
    def _on_tab_changed(self, _index: int) -> None:
        sub = self.stack.currentWidget()
        if sub is not None:
            self.command_bar.bind_subpage(sub)
            self.command_bar.set_running(sub.is_test_running)
        self._auto_prompt_current_config()

    def _on_sub_run_state(self, _state) -> None:
        """任一子页运行态变化：仅当其是当前子页时联动 CommandBar。"""
        sub = self.stack.currentWidget()
        if sub is not None:
            self.command_bar.set_running(sub.is_test_running)

    def _on_sub_config_name_changed(self) -> None:
        sub = self.stack.currentWidget()
        if sub is not None:
            self.command_bar.set_config_name(sub.config_display_name())

    def _on_connection_settings(self) -> None:
        sub = self.stack.currentWidget()
        if sub is not None and hasattr(sub, "show_connection_panel"):
            sub.show_connection_panel()

    def _call_current(self, method: str) -> None:
        sub = self.stack.currentWidget()
        handler = getattr(sub, method, None)
        if callable(handler):
            handler()

    def _auto_prompt_current_config(self) -> None:
        sub = self.stack.currentWidget()
        test_key = self.get_current_test()
        if sub is None or test_key in self._config_prompted:
            return
        self._config_prompted.add(test_key)
        if hasattr(sub, "prompt_config_manager_once"):
            sub.prompt_config_manager_once()

    # ------------------------------------------------------------------ 契约 API
    def set_current_test(self, test_key: str) -> None:
        index = self.TEST_TAB_MAP.get(test_key, 0)
        if index != self.stack.currentIndex():
            self.stack.setCurrentIndex(index)
        if test_key != self.command_bar.current_module():
            self.command_bar.set_current_module(test_key, emit=False)

    def get_current_test(self) -> str:
        index = self.stack.currentIndex()
        reverse_map = {v: k for k, v in self.TEST_TAB_MAP.items()}
        return reverse_map.get(index, "ldo")

    def _sync_from_top(self) -> None:
        for sub_ui in (self.ldo_test_ui, self.dcdc_test_ui):
            if hasattr(sub_ui, "sync_n6705c_from_top"):
                sub_ui.sync_n6705c_from_top()
            if hasattr(sub_ui, "sync_oscilloscope_from_top"):
                sub_ui.sync_oscilloscope_from_top()

    def get_test_config(self, test_type: str):
        sub = self.ldo_test_ui if test_type == "ldo" else self.dcdc_test_ui
        return sub.get_test_config()

    def update_test_result(self, test_type: str, result) -> None:
        sub = self.ldo_test_ui if test_type == "ldo" else self.dcdc_test_ui
        sub.update_test_result(result)

    def clear_all_results(self) -> None:
        self.ldo_test_ui.clear_results()
        self.dcdc_test_ui.clear_results()

    def set_system_status(self, status: str, is_error: bool = False) -> None:
        self.ldo_test_ui.set_system_status(status, is_error)
        self.dcdc_test_ui.set_system_status(status, is_error)

    # ------------------------------------------------------------------ AI Assistant 透传
    # 容器自身不实现 AI 契约（ai_capabilities / ai_get_config / ai_start_test /
    # ai_stop_test / ai_get_result_summary 由子页基类 _sections/ai_contract.py 的
    # ModuleTestAIContract mixin 提供）；此处仅透传枢纽路由所需的下钻入口与日志
    # 读 / 回填接口，参考 ConsumptionTestWrapper 的同名实现。
    def _current_ai_subpage(self):
        """返回当前子页实例（供 AI 枢纽路由用）。"""
        return self.stack.currentWidget() if self.stack is not None else None

    @property
    def tab_widget(self):
        """tab_widget 别名：暴露 QStackedWidget 供 AI 枢纽下钻到当前子页。

        枢纽 resolve_active_ai_page 对 Tab 容器页（pmu_test / charger_test /
        module_test / consumption_test / vmin_hunter）按约定
        ``getattr(container, "tab_widget", None).currentWidget()`` 取当前子页；
        本页 P3 重构后用 ``QStackedWidget``（``self.stack``，非 QTabWidget），此处
        透传以对齐路由契约，使子页的 AI 能力集 / 配置 / 启停 / 结果摘要可被命中。
        """
        return self.stack

    @property
    def logs_frame(self):
        """logs_frame 透传：把当前子页的 ExecutionLogsFrame 暴露给 AI 枢纽。

        枢纽 _get_ai_execution_logs 经 ``page.logs_frame._all_logs`` 读取日志；
        wrapper 自身不持 logs 控件，按当前子页下钻到 ``detail_dock.log_panel.frame``
        （ExecutionLogsFrame，持 ``_all_logs``；LogPanel 是其批量 flush 包装层）。
        """
        sub = self._current_ai_subpage()
        if sub is None:
            return None
        log_panel = getattr(getattr(sub, "detail_dock", None), "log_panel", None)
        if log_panel is None:
            return None
        return getattr(log_panel, "frame", None)

    def append_log(self, message: str) -> None:
        """append_log 透传：让 AI 枢纽 _ai_ui_invoke 的 [AI] 日志回填落到当前子页。

        枢纽 _current_active_page 返回 wrapper（不下钻），经 getattr(page,
        'append_log', None) 找不到时静默失败。此处透传到当前子页的 LogPanel，
        保证 [AI] 触发 XXX 日志条目能正确出现在 ExecutionLogsFrame。
        """
        sub = self._current_ai_subpage()
        if sub is None:
            return
        log_panel = getattr(getattr(sub, "detail_dock", None), "log_panel", None)
        if log_panel is not None:
            log_panel.append_log(message)


if __name__ == "__main__":
    import sys

    from PySide6.QtGui import QColor, QFont, QPalette
    from PySide6.QtWidgets import QApplication

    from ui.standalone import resize_and_center_window
    from ui.theme import configure_high_dpi

    # 复刻 main.py / MainWindow._setup_style 的 app 级初始化，使本页 standalone
    # 渲染环境与内嵌于 MainWindow 时一致：深色 palette + Segoe UI 字体 + QToolTip
    # 深底 QSS。否则未设 QSS 的控件（含本顶层 QWidget 背景）回落默认浅色 →
    # 页面发白、构造期多次 setStyleSheet 重绘时闪白框。
    configure_high_dpi()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(2, 6, 24))
    palette.setColor(QPalette.WindowText, QColor(200, 200, 200))
    palette.setColor(QPalette.Base, QColor(32, 35, 40))
    palette.setColor(QPalette.AlternateBase, QColor(40, 43, 48))
    palette.setColor(QPalette.ToolTipBase, QColor(40, 43, 48))
    palette.setColor(QPalette.ToolTipText, QColor(200, 200, 200))
    palette.setColor(QPalette.Text, QColor(200, 200, 200))
    palette.setColor(QPalette.Button, QColor(50, 53, 58))
    palette.setColor(QPalette.ButtonText, QColor(200, 200, 200))
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, QColor(30, 30, 30))
    app.setPalette(palette)
    app.setFont(QFont("Segoe UI", 9))
    app.setStyleSheet("""
        QToolTip {
            background-color: #282c30;
            color: #d7dce2;
            border: 1px solid #4a5568;
            padding: 4px 6px;
        }
    """)

    window = ModuleTestUI()
    window.setWindowTitle("Module Test")
    resize_and_center_window(window)
    window.show()

    sys.exit(app.exec())
