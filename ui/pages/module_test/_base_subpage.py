"""Module Test 子页面基类（LDO / DCDC 共用）——装配 + 对外契约 + run flow。

布局（P3）：InfoBanner ×2 → LeftRail(连接/DUT Card) + QSplitter(TestPlanPanel
| DetailDock 结果/日志) → RunControlBar。子类仅靠 5 个类属性差异化
（MODULE_TYPE / PAGE_KEY / ITEMS_REGISTRY / RUNNER_CLS / STANDALONE_ITEMS，
新增模块 ≤15 行）。运行态由 RunState + _apply_run_state() 单一入口驱动。
对外契约（公共 API / AI 契约 / 构造透传）与重构前完全一致。
"""
from __future__ import annotations

import os
import time
from typing import Any

from PySide6.QtCore import Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import QHBoxLayout, QSplitter, QVBoxLayout, QWidget

from core.module_test._common import cfg_int
from core.module_test.module_config import ModuleConfigWorker
from debug_config import DEBUG_MOCK
from log_config import get_logger
from ui.modules.n6705c_module_frame import N6705CConnectionMixin
from ui.modules.oscilloscope_module_frame import OscilloscopeConnectionMixin
from ui.pages.module_test._sections.ai_contract import ModuleTestAIContract
from ui.pages.module_test._sections.config_store import ModuleConfigStore
from ui.pages.module_test._sections.detail_dock import DetailDock
from ui.pages.module_test._sections.left_rail import LeftRail
from ui.pages.module_test._sections.test_plan_panel import TestPlanPanel
from ui.pages.module_test.dialogs.config_manager_dialog import ConfigManagerDialog
from ui.pages.module_test.dialogs.item_params_dialog import ItemParamsDialog
from ui.pages.module_test.dialogs.judge_dialog import JudgeCriteriaDialog
from ui.theme import apply_qss
from ui.widgets.banner import InfoBanner
from ui.widgets.run_control_bar import RunControlBar, RunState
from ui.widgets.toast import Toast

_logger = get_logger(__name__)


class ModuleTestSubPageBase(QWidget, N6705CConnectionMixin,
                            OscilloscopeConnectionMixin, ModuleTestAIContract):
    """LDO/DCDC 子页面共用基类（装配 + 契约 + run flow）。"""

    MODULE_TYPE: str = ""
    PAGE_KEY: str = ""
    ITEMS_REGISTRY: dict[str, tuple[str, Any, bool, bool, Any]] = {}
    RUNNER_CLS: type = None  # type: ignore[assignment]
    STANDALONE_ITEMS: tuple[str, ...] = ()

    # 顶层 CommandBar / 枢纽监听用（附加信号，不破坏既有契约）
    connectionStateChanged = Signal()
    runStateChanged = Signal(object)      # RunState
    configNameChanged = Signal()

    def __init__(self, *, n6705c_top=None, mso64b_top=None, chamber_ui=None,
                 instrument_manager=None, ui_action_registry=None):
        super().__init__()
        self._n6705c_top = n6705c_top
        self._mso64b_top = mso64b_top
        self._chamber_ui = chamber_ui
        self._instrument_manager = instrument_manager
        self._ui_action_registry = ui_action_registry

        self.init_n6705c_connection(n6705c_top, instrument_manager=instrument_manager)
        self.init_oscilloscope_connection(mso64b_top, instrument_manager=instrument_manager)

        self._runner = None
        self.is_test_running = False
        self._run_state = RunState.IDLE
        self._last_result = None
        self._last_report_path: str | None = None
        self._item_overrides: dict[str, dict] = {}
        # 判定标准（PASS/FAIL Criteria）：随模块配置保存/加载，runner 据此判项
        self._judge_criteria: dict[str, dict] = {}
        self._current_config_path: str | None = None
        self._config_prompted = False
        self._run_start_ts = 0.0
        self._item_start_ts: dict[str, float] = {}
        self._counts = {"pass": 0, "fail": 0, "na": 0}
        # Module Config 后台执行线程（手动执行 / 测试前自动执行共用）
        self._modcfg_thread: QThread | None = None
        self._modcfg_worker: ModuleConfigWorker | None = None
        self._modcfg_after = None  # 执行完成后的回调（如继续启动测试）

        self._build_ui()
        self._wire_shortcuts()
        self.sync_n6705c_from_top()
        self.sync_oscilloscope_from_top()
        # 初始同步一次 scope 状态到测试项表（未连接时 (scope) 项显示"未接示波器"）
        self.test_plan.set_scope_connected(bool(self.scope_connected))
        self._register_ai_ui_actions()
        self._apply_run_state(RunState.IDLE)

    # ================================================================== UI 装配
    def _build_ui(self) -> None:
        apply_qss(self, "controls")
        apply_qss(self, "table")
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._config_banner = InfoBanner(
            "尚未加载配置：可选择已有配置，或使用默认设置直接开始。",
            actions=[("choose", "选择配置"), ("default", "使用默认")], severity="info")
        self._config_banner.actionTriggered.connect(self._on_config_banner_action)
        self._config_banner.hide()
        root.addWidget(self._config_banner)
        self._alert_banner = InfoBanner("", severity="warning")
        self._alert_banner.hide()
        root.addWidget(self._alert_banner)

        body = QHBoxLayout()
        body.setSpacing(8)
        self.left_rail = LeftRail(self, self.MODULE_TYPE)
        self.left_rail.module_config_panel.execRequested.connect(
            self._on_exec_module_config)
        body.addWidget(self.left_rail)
        center = QVBoxLayout()
        center.setSpacing(6)
        self.test_plan = TestPlanPanel(self.ITEMS_REGISTRY, self.STANDALONE_ITEMS)
        self.test_plan.paramsRequested.connect(self._open_item_params)
        self.detail_dock = DetailDock()
        self.detail_dock.openReportRequested.connect(self._on_open_report)
        self.detail_dock.openOutputDirRequested.connect(self._on_open_output_dir)
        self.detail_dock.clearResultsRequested.connect(self._on_clear_results)
        self.detail_dock.locateLogRequested.connect(self._on_locate_log)
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.test_plan)
        splitter.addWidget(self.detail_dock)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        center.addWidget(splitter, 1)
        body.addLayout(center, 1)
        root.addLayout(body, 1)

        self.run_bar = RunControlBar()
        self.run_bar.startRequested.connect(self._on_start_test)
        self.run_bar.stopRequested.connect(self._on_stop_test)
        root.addWidget(self.run_bar)
        self._store = ModuleConfigStore(
            module_type=self.MODULE_TYPE, dut_panel=self.left_rail.dut_panel,
            test_plan=self.test_plan, item_overrides=self._item_overrides,
            items_registry=self.ITEMS_REGISTRY,
            module_config_panel=self.left_rail.module_config_panel,
            judge_criteria=self._judge_criteria)

    def _wire_shortcuts(self) -> None:
        QShortcut(QKeySequence("F5"), self, activated=self._on_start_test)
        QShortcut(QKeySequence(Qt.Key_Escape), self,
                  activated=self.run_bar.stop_btn.click)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._on_save_config)
        QShortcut(QKeySequence("Ctrl+O"), self, activated=self._on_open_config)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.test_plan.focus_search)
        QShortcut(QKeySequence("Ctrl+L"), self,
                  activated=self.detail_dock.log_panel.clear_log)

    # ================================================================== 运行状态机
    def _apply_run_state(self, state: RunState) -> None:
        """单一入口：控件禁用矩阵 / 左栏折叠 / Tab 跳转 / 信号广播。"""
        self._run_state = state
        running = state in (RunState.PRECHECK, RunState.RUNNING,
                            RunState.PAUSED, RunState.STOPPING)
        self.is_test_running = running
        self.run_bar.set_state(state)
        self.left_rail.connection_card.setEnabled(not running)
        self.left_rail.config_card.setEnabled(not running)
        self.left_rail.module_config_card.setEnabled(not running)
        self.left_rail.set_running(running)
        if state is RunState.RUNNING:
            self.detail_dock.show_log_tab()
        elif state is RunState.FINISHED:
            self.detail_dock.show_result_tab()
        self.runStateChanged.emit(state)

    # ================================================================== precheck
    def _precheck(self, cfg: dict) -> bool:
        """启动前校验：未勾选 / 必填字段 / 仪器缺失 → Banner + 高亮，不弹窗。"""
        if not cfg["selected_items"]:
            self._show_alert("未勾选任何测试项，请先在测试项清单中勾选。", "info")
            return False
        err_row = self.left_rail.dut_panel.validate()
        if err_row is not None:
            self._show_alert("必填字段缺失或无效，请检查 DUT 配置（红框标注）。", "error")
            self.left_rail.config_card.set_expanded(True)
            err_row.editor.setFocus()
            return False
        missing = self._missing_instruments(cfg)
        if missing:
            detail = "；".join(missing)
            self._show_alert(f"仪器未连接，无法开始测试：{detail}", "error")
            self.left_rail.show_connection()
            return False
        self._alert_banner.hide()
        return True

    def _show_alert(self, text: str, severity: str = "warning") -> None:
        self._alert_banner.set_text(text)
        self._alert_banner.set_severity(severity)
        self._alert_banner.show()

    def _missing_instruments(self, cfg: dict) -> list[str]:
        """汇总本次勾选项全程所需但未连接的仪器（空列表=齐全，DEBUG_MOCK 放行）。"""
        if DEBUG_MOCK:
            return []
        missing: list[str] = []
        if not self.is_connected or self.n6705c is None:
            missing.append("N6705C 电源分析仪")
        scope_names = [self.ITEMS_REGISTRY[k][0] for k in cfg.get("selected_items", [])
                       if k in self.ITEMS_REGISTRY and self.ITEMS_REGISTRY[k][2]]
        if scope_names and not self.scope_connected:
            missing.append(f"示波器（{len(scope_names)} 个勾选项需要：{'、'.join(scope_names)}）")
        return missing

    # ================================================================== Module Config 执行
    def _on_exec_module_config(self) -> None:
        """手动执行：立即经 I2C 下发 Module Config（不启动测试）。"""
        if self.is_test_running:
            return
        self._run_module_config(after=None)

    def _run_module_config(self, after) -> None:
        """后台执行 Module Config；``after`` 为成功/失败后都要调用的回调（可为 None）。

        手动执行与测试前自动执行共用此链路：解析/下发在 QThread，UI 不阻塞。
        """
        if self._modcfg_thread is not None:
            self.detail_dock.log_panel.append_log("[MODCFG] 上一次模块配置仍在执行中")
            return
        panel = self.left_rail.module_config_panel
        text = panel.config_text()
        if not text:
            self.detail_dock.log_panel.append_log("[MODCFG] 配置为空，跳过执行")
            if after is not None:
                after(True)
            return
        cfg = self.get_test_config()
        try:
            device_addr = cfg_int(cfg, "device_addr", 0)
            width_flag = int(cfg.get("width_flag", 0))
        except (ValueError, TypeError):
            self.detail_dock.log_panel.append_log(
                "[MODCFG] [ERROR] Device 地址 / Width Flag 无效，无法执行")
            if after is not None:
                after(False)
            return

        panel.set_running(True)
        self._modcfg_after = after
        worker = ModuleConfigWorker(
            config_text=text, device_addr=device_addr, width_flag=width_flag,
            is_mock=DEBUG_MOCK, n6705c=self.n6705c)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.log.connect(self.detail_dock.log_panel.append_log)
        worker.finished.connect(self._on_modcfg_finished)
        worker.finished.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_modcfg_thread_cleaned)
        self._modcfg_thread = thread
        self._modcfg_worker = worker
        self.detail_dock.log_panel.append_log("[MODCFG] 模块配置后台执行开始")
        thread.start()

    def _on_modcfg_finished(self, ok: bool, msg: str) -> None:
        self.left_rail.module_config_panel.set_running(False)
        level = "" if ok else "[ERROR] "
        self.detail_dock.log_panel.append_log(f"[MODCFG] {level}{msg}")
        after, self._modcfg_after = self._modcfg_after, None
        if after is not None:
            after(ok)

    def _on_modcfg_thread_cleaned(self) -> None:
        self._modcfg_thread = None
        self._modcfg_worker = None

    # ================================================================== run flow
    def _on_start_test(self) -> None:
        if self.is_test_running:
            return
        self._apply_run_state(RunState.PRECHECK)
        cfg = self.get_test_config()
        if not self._precheck(cfg):
            self._apply_run_state(RunState.IDLE)
            return

        # 勾选「测试前执行模块配置」：先后台下发 Module Config，完成后再启动测试
        if cfg.get("module_config_enabled") and cfg.get("module_config_yaml"):
            self.detail_dock.log_panel.append_log(
                "[MODCFG] 测试前执行模块配置（勾选启用）")
            self._run_module_config(after=lambda _ok: self._proceed_start_test(cfg))
            return
        self._proceed_start_test(cfg)

    def _proceed_start_test(self, cfg: dict) -> None:
        scope = self.Osc_ins if self.scope_connected else None
        self._runner = self.RUNNER_CLS(
            config=cfg, n6705c=self.n6705c, scope=scope, chamber=None,
        )
        self._runner.progress.connect(self._on_progress)
        self._runner.item_started.connect(self._on_item_started)
        self._runner.item_finished.connect(self._on_item_finished)
        self._runner.log.connect(self.detail_dock.log_panel.append_log)
        self._runner.finished_result.connect(self._on_finished)
        self._runner.failed.connect(self._on_failed)

        selected = cfg["selected_items"]
        self._counts = {"pass": 0, "fail": 0, "na": 0}
        self._item_start_ts = {}
        self._run_start_ts = time.monotonic()
        self.run_bar.set_total_text(f"0/{len(selected)}")
        self.run_bar.set_counts(0, 0, 0)
        self.run_bar.set_current_item("准备中…")
        self.test_plan.enter_run_state(selected)
        self.detail_dock.log_panel.start_timer(len(selected))
        self.detail_dock.log_panel.append_log(
            f"[START] {self.MODULE_TYPE.upper()} Module Test 启动")
        self.set_system_status("测试进行中")
        self._apply_run_state(RunState.RUNNING)
        self._runner.start()

    def _on_stop_test(self) -> None:
        if self._runner is not None and self.is_test_running:
            self._apply_run_state(RunState.STOPPING)
            self.detail_dock.log_panel.append_log("[STOP] 请求停止测试...")
            self._runner.request_stop()

    def _on_progress(self, percent: int, label: str) -> None:
        self.run_bar.set_progress(percent)
        self.detail_dock.log_panel.set_progress(percent)

    def _on_item_started(self, item_key: str) -> None:
        self._item_start_ts[item_key] = time.monotonic()
        self.test_plan.mark_item_running(item_key)
        name = self.ITEMS_REGISTRY.get(item_key, (item_key,))[0]
        self.run_bar.set_current_item(f"当前: {name}")
        done = self._counts["pass"] + self._counts["fail"] + self._counts["na"]
        total = len(self._item_start_ts) and self.test_plan.selected_keys() or []
        self.run_bar.set_total_text(f"{done}/{len(total) if total else '—'}")

    def _on_item_finished(self, item_key: str, summary: dict) -> None:
        verdict = summary.get("passed", "N/A")
        start = self._item_start_ts.pop(item_key, None)
        if start is not None:
            self.test_plan.set_item_duration(item_key, time.monotonic() - start)
        self.test_plan.mark_item_done(item_key, verdict)
        key = "pass" if verdict == "PASS" else ("fail" if verdict == "FAIL" else "na")
        self._counts[key] += 1
        done = sum(self._counts.values())
        selected = self.test_plan.selected_keys()
        self.run_bar.set_counts(self._counts["pass"], self._counts["fail"],
                                self._counts["na"])
        self.run_bar.set_total_text(f"{done}/{len(selected)}")
        self.run_bar.set_timing(time.monotonic() - self._run_start_ts, None)
        self.detail_dock.log_panel.update_step(done, item_key)
        self.detail_dock.log_panel.append_log(f"[ITEM] {item_key} -> {verdict}")

    def _on_finished(self, result) -> None:
        self._last_result = result
        self.detail_dock.log_panel.flush_now()
        self.detail_dock.log_panel.stop_timer()
        self.test_plan.exit_run_state()
        self._last_report_path = result.summary.get("report_path")
        self.detail_dock.set_report_available(self._last_report_path is not None)
        self.set_system_status("就绪")
        s = result.summary
        self.detail_dock.log_panel.append_log(
            f"[DONE] 总体 {s.get('overall', 'N/A')}（PASS {s.get('pass', 0)}/"
            f"FAIL {s.get('fail', 0)}/N/A {s.get('norec', 0)}）"
        )
        elapsed = time.monotonic() - self._run_start_ts
        self.detail_dock.set_result(result, elapsed)
        self.run_bar.set_current_item("完成")
        self.run_bar.set_timing(elapsed, None)
        self._apply_run_state(RunState.FINISHED)
        Toast.popup(self, f"测试完成：总体 {s.get('overall', 'N/A')}",
                    severity="success" if s.get("overall") == "PASS" else "warning")

    def _on_failed(self, msg: str) -> None:
        self.detail_dock.log_panel.flush_now()
        self.detail_dock.log_panel.stop_timer()
        self.test_plan.exit_run_state()
        self.set_system_status("测试失败", is_error=True)
        self.detail_dock.log_panel.append_log(f"[ERROR] {msg}")
        self._show_alert(f"测试失败：{msg}", "error")
        self._apply_run_state(RunState.ERROR)

    def _on_locate_log(self, keyword: str) -> None:
        self.detail_dock.show_log_tab()
        self.detail_dock.log_panel.locate(keyword)

    # ================================================================== 参数弹窗
    def _open_item_params(self, item_key: str) -> None:
        spec = self.ITEMS_REGISTRY.get(item_key)
        if not spec:
            return
        name, _run_fn, _needs_scope, _checked, params = spec
        dlg = ItemParamsDialog(
            title=f"参数设置 - {name}",
            specs=params,
            current_override=self._item_overrides.get(item_key, {}),
            base_value_fn=self._base_param_value,
            parent=self,
        )
        if dlg.exec():
            override = dlg.get_override()
            if override:
                self._item_overrides[item_key] = override
            else:
                self._item_overrides.pop(item_key, None)
            self.test_plan.set_item_customized(item_key, bool(override))

    def _base_param_value(self, base_key: str):
        """按 ParamSpec.base_key 从被测配置界面取当前值作弹窗预填。"""
        return self.get_test_config().get(base_key)

    # ================================================================== 判定标准
    def _on_open_judge_criteria(self) -> None:
        """打开判定标准弹窗（CommandBar「判断标准」按钮，运行中禁止）。"""
        if self.is_test_running:
            return
        dlg = JudgeCriteriaDialog(self.ITEMS_REGISTRY, self._judge_criteria,
                                  parent=self)
        if dlg.exec():
            # 原地更新，保持与 ModuleConfigStore 共享的引用
            self._judge_criteria.clear()
            self._judge_criteria.update(dlg.get_criteria())
            n_rules = sum(len(v.get("rules", ()))
                          for v in self._judge_criteria.values())
            self.detail_dock.log_panel.append_log(
                f"[JUDGE] 判定标准已更新：{len(self._judge_criteria)} 个测试项 / "
                f"{n_rules} 条规则" if n_rules else "[JUDGE] 判定标准已清空")

    # ================================================================== 配置 IO（委托 ModuleConfigStore）
    def get_test_config(self) -> dict[str, Any]:
        return self._store.collect()

    def config_display_name(self) -> str:
        return (os.path.basename(self._current_config_path)
                if self._current_config_path else "")

    def _on_config_banner_action(self, key: str) -> None:
        if key == "choose":
            self._on_open_config()
        self._config_banner.hide()

    def _save_config_to(self, path: str) -> None:
        cfg = self.get_test_config()
        if self._store.write_file(path, cfg):
            self._current_config_path = path
            self.detail_dock.log_panel.append_log(
                f"[INFO] 配置已保存：{os.path.basename(path)}")
            Toast.popup(self, "配置已保存", severity="success")
            self.configNameChanged.emit()
        else:
            self._show_alert("配置写入失败，详见日志。", "error")

    def _on_save_config(self) -> None:
        if self._current_config_path:
            self._save_config_to(self._current_config_path)
        else:
            self._on_save_config_as()

    def _on_save_config_as(self) -> None:
        path = self._store.prompt_save_path(self)
        if path:
            self._save_config_to(path)

    def _on_open_config(self) -> None:
        dlg = ConfigManagerDialog(self._store.configs_root(), self.MODULE_TYPE, parent=self)
        if dlg.exec() != ConfigManagerDialog.Accepted:
            return
        self._apply_selected_config(dlg)

    def _apply_selected_config(self, dlg) -> None:
        path = dlg.selected_path()
        if not path:
            return
        cfg = self._store.read_file(path)
        if cfg is None:
            self._show_alert("配置文件无效或损坏，详见日志。", "error")
            return
        self._store.restore(cfg)
        self._current_config_path = path
        self.detail_dock.log_panel.append_log(
            f"[INFO] 已加载配置：{os.path.basename(path)}")
        Toast.popup(self, f"已加载配置：{os.path.basename(path)}", severity="success")
        self.configNameChanged.emit()

    def prompt_config_manager_once(self, *, force_dialog: bool = False) -> None:
        """首次进入本模块测试页提示加载配置（每子页一次）。

        默认改为非模态 InfoBanner；``force_dialog=True`` 兼容旧的弹窗行为。
        """
        if self._config_prompted:
            return
        self._config_prompted = True
        if force_dialog:
            QTimer.singleShot(0, self._show_config_manager_modeless)
        elif self._current_config_path is None:
            QTimer.singleShot(0, self._config_banner.show)

    def _show_config_manager_modeless(self) -> None:
        dlg = ConfigManagerDialog(self._store.configs_root(), self.MODULE_TYPE, parent=self)
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dlg.setModal(False)
        dlg.accepted.connect(lambda: self._apply_selected_config(dlg))
        dlg.show()

    # ================================================================== 动作
    def _on_open_report(self) -> None:
        path = self._last_report_path
        if path and os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.detail_dock.log_panel.append_log("[WARN] 报告文件不存在。")

    def _on_open_output_dir(self) -> None:
        path = self._last_report_path
        directory = (os.path.dirname(path) if path else
                     os.path.abspath("Results"))
        if os.path.isdir(directory):
            QDesktopServices.openUrl(QUrl.fromLocalFile(directory))

    def _on_clear_results(self) -> None:
        self._last_result = None
        self._last_report_path = None
        self.detail_dock.set_report_available(False)
        self.detail_dock.clear_summary()
        self.detail_dock.result_table.clear()
        self.detail_dock.log_panel.clear_log()
        self.detail_dock.log_panel.set_progress(0)
        self.run_bar.set_counts(0, 0, 0)
        self.run_bar.set_total_text("-/-")
        self.run_bar.set_progress(0)
        self.detail_dock.log_panel.append_log("[INFO] 已清空结果。")

    def _on_select_all_items(self) -> None:
        self.test_plan.toggle_all()

    # ================================================================== 公共 API（契约，签名不变）
    def update_test_result(self, result) -> None:
        self._last_result = result
        if result is not None and hasattr(result, "summary"):
            self._last_report_path = result.summary.get("report_path")
            self.detail_dock.set_result(result, None)

    def clear_results(self) -> None:
        self._on_clear_results()

    def set_system_status(self, status: str, is_error: bool = False) -> None:
        if hasattr(self, "system_status_label"):
            text = status if status.startswith("●") else f"● {status}"
            self.system_status_label.setText(text)
            if is_error:
                obj = "statusErr"
            elif any(kw in status for kw in ("Searching", "Connecting",
                                              "Disconnecting", "Running", "进行中")):
                obj = "statusWarn"
            else:
                obj = "statusOk"
            self.system_status_label.setObjectName(obj)
            self.system_status_label.style().unpolish(self.system_status_label)
            self.system_status_label.style().polish(self.system_status_label)
        self.connectionStateChanged.emit()

    def set_scope_status(self, status, is_error: bool = False) -> None:
        """示波器状态经此 funnel（mixin 各路径），顺带广播连接态。"""
        super().set_scope_status(status, is_error)
        self.connectionStateChanged.emit()

    def _update_n6705c_connect_button_state(self, connected: bool) -> None:
        super()._update_n6705c_connect_button_state(connected)
        self.connectionStateChanged.emit()

    def update_instrument_info(self, instrument_info) -> None:
        pass

    def sync_n6705c_from_top(self) -> None:
        super().sync_n6705c_from_top()
        self.connectionStateChanged.emit()

    def sync_oscilloscope_from_top(self) -> None:
        super().sync_oscilloscope_from_top()
        if hasattr(self, "test_plan"):
            self.test_plan.set_scope_connected(self.scope_connected)
        self.connectionStateChanged.emit()

    def _on_mso64b_top_changed(self) -> None:
        """顶层示波器连接变化时联动刷新 (scope) 项提示（运行期除外）。"""
        super()._on_mso64b_top_changed()
        if getattr(self, "is_test_running", False):
            return
        if hasattr(self, "test_plan"):
            self.test_plan.set_scope_connected(self.scope_connected)
        self.connectionStateChanged.emit()

    def show_connection_panel(self) -> None:
        self.left_rail.show_connection()
    # AI 契约（ai_* / _register_ai_ui_actions）由 _sections/ai_contract.py 的
    # ModuleTestAIContract mixin 提供。
