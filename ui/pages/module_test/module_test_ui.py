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
        self.command_bar.judgeCriteriaRequested.connect(
            lambda: self._call_current("_on_open_judge_criteria"))
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
