"""AISettingsDialog：AI 设置入口（标签页）+ 「测试连接」+ 白名单管理。

标签页：
  - 常规：连接 / 模型 / 流式 / 超时 / 日志 / 脱敏等基础配置（落盘 AISettings.save）；
  - 白名单：管理常驻白名单（auto_approve）与黑名单（blocked），落盘 policy.json。

遵守约定：parent=self；OK/Cancel/Test 按钮 default/autoDefault 显式二元化；
API Key 输入框用 EchoMode.Password，落盘走 AISettings.save（不展示 env 注入值）。
"""
from __future__ import annotations

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.ai.ai_service import AIService
from log_config import get_logger

from ui.ai.dialog_theme import apply_ai_dialog_theme

logger = get_logger(__name__)

_DIALOG_STYLE = """
QDialog, QDialog * {
    font-family: "Segoe UI", "Microsoft YaHei UI", "Inter", system-ui, sans-serif;
}
QDialog { background-color: #070709; }
QLabel { color: #cbd5e1; font-size: 12px; background: transparent; border: none; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #070709; color: #e2e8f0;
    border: 1px solid #1e293b; border-radius: 6px; padding: 4px 8px;
    min-height: 22px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #3b82f6;
}
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background-color: #0f172a; color: #cbd5e1;
    border: 1px solid #1e293b; selection-background-color: #1e293b;
}
QCheckBox { color: #cbd5e1; font-size: 12px; font-weight: 700; }
QListWidget {
    background-color: #070709; color: #cbd5e1;
    border: 1px solid #1e293b; border-radius: 6px;
    font-size: 11px;
}
QListWidget::item { padding: 4px 6px; }
QListWidget::item:selected { background-color: #1e293b; }
QTabWidget::pane { border: 1px solid #1e293b; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background-color: #0f172a; color: #94a3b8;
    border: 1px solid #1e293b; border-bottom: none;
    padding: 5px 16px; margin-right: 2px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    font-size: 12px;
}
QTabBar::tab:selected { background-color: #121629; color: #e2e8f0; }
QPushButton {
    min-height: 28px; padding: 4px 16px;
    border: 1px solid #1e293b; border-radius: 6px;
    background-color: #0f172a; color: #cbd5e1; font-weight: 600; font-size: 12px;
}
QPushButton:hover { background-color: #1e293b; border: 1px solid #334155; }
QPushButton#aiOkBtn { background-color: #5b3df5; border: 1px solid #5b3df5; color: #ffffff; }
QLabel#aiTestResult { font-size: 11px; }
QLabel#aiHint { color: #94a3b8; font-size: 11px; font-weight: 700; }
"""


class AISettingsDialog(QDialog):
    def __init__(self, service: AIService, parent=None):
        super().__init__(parent)
        self._service = service
        self._settings = service.settings
        self._policy = service.dispatcher.policy if service.dispatcher else None
        self.setWindowTitle("AI 设置")
        self.setMinimumWidth(460)
        apply_ai_dialog_theme(self, _DIALOG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "常规")
        tabs.addTab(self._build_waveform_tab(), "波形算法")
        tabs.addTab(self._build_whitelist_tab(), "白名单")
        tabs.addTab(self._build_experience_tab(), "本机经验")
        root.addWidget(tabs)
        self._eval_thread = None
        self._eval_worker = None

        self._test_result = QLabel("")
        self._test_result.setObjectName("aiTestResult")
        self._test_result.setWordWrap(True)
        root.addWidget(self._test_result)

        root.addLayout(self._build_button_bar())

        self._service.connection_tested.connect(self._on_connection_tested)
        self._service.models_probed.connect(self._on_models_probed)

    def _build_general_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(8)

        self._enabled_chk = QCheckBox("启用 AI 助手")
        self._enabled_chk.setChecked(self._settings.enabled)
        form.addRow("", self._enabled_chk)

        self._base_url_edit = QLineEdit(self._settings.base_url)
        self._base_url_edit.setPlaceholderText("http://172.16.10.84:3000/v1")
        form.addRow("Base URL", self._base_url_edit)

        self._api_key_edit = QLineEdit(self._settings.api_key)
        self._api_key_edit.setEchoMode(QLineEdit.Password)
        self._api_key_edit.setPlaceholderText("sk-...（留空则用环境变量 KK_LAB_AI_API_KEY）")
        form.addRow("API Key", self._api_key_edit)

        self._mode_combo = QComboBox()
        self._mode_combo.addItem("自动（按页面）", "auto")
        self._mode_combo.addItem("固定模型", "fixed")
        mode_idx = self._mode_combo.findData(self._settings.model_mode)
        self._mode_combo.setCurrentIndex(mode_idx if mode_idx >= 0 else 1)
        self._mode_combo.setToolTip(
            "自动：按当前页面 Profile 选择模型；固定：所有页面统一使用下方默认模型"
        )
        form.addRow("模型模式", self._mode_combo)

        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        self._model_combo.addItems(self._settings.available_models)
        self._model_combo.setCurrentText(self._settings.default_model)
        self._model_combo.setToolTip("固定模式下统一使用的模型；可手动输入网关支持的模型名")
        form.addRow("默认模型", self._model_combo)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self._on_mode_changed()

        self._models_edit = QLineEdit(", ".join(self._settings.available_models))
        self._models_edit.setPlaceholderText("deepseekv4flash, glm-5.1-fp8")
        self._models_edit.setToolTip("可选模型清单（逗号分隔），用于面板手动切换")
        form.addRow("可选模型", self._models_edit)

        self._stream_chk = QCheckBox("流式输出（逐字返回）")
        self._stream_chk.setChecked(self._settings.stream)
        form.addRow("", self._stream_chk)

        self._timeout_spin = QSpinBox()
        self._timeout_spin.setRange(5, 600)
        self._timeout_spin.setValue(int(self._settings.timeout_seconds))
        form.addRow("超时 (s)", self._timeout_spin)

        self._log_lines_spin = QSpinBox()
        self._log_lines_spin.setRange(10, 2000)
        self._log_lines_spin.setValue(int(self._settings.max_recent_log_lines))
        form.addRow("日志行数 (行)", self._log_lines_spin)

        self._masking_chk = QCheckBox("发送前脱敏敏感信息")
        self._masking_chk.setChecked(self._settings.enable_log_masking)
        form.addRow("", self._masking_chk)

        self._summary_chk = QCheckBox("历史过长时自动压缩前情提要")
        self._summary_chk.setChecked(self._settings.enable_history_summary)
        form.addRow("", self._summary_chk)

        self._curator_ai_chk = QCheckBox("AI 辅助沉淀（润色草稿，关闭则走规则兜底）")
        self._curator_ai_chk.setChecked(self._settings.curator_ai_assist_enabled)
        form.addRow("", self._curator_ai_chk)

        self._telemetry_chk = QCheckBox("匿名经验上报（脱敏，关闭后彻底不采集不上报）")
        self._telemetry_chk.setChecked(self._settings.telemetry_enabled)
        form.addRow("", self._telemetry_chk)

        layout.addLayout(form)
        layout.addStretch(1)
        return tab

    def _build_waveform_tab(self) -> QWidget:
        """波形事件检测算法选择 + 随算法动态切换的常用参数（落盘 AISettings）。"""
        from core.ai.algorithms import available, get

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        hint = QLabel(
            "选择「Send Waveform to AI」时使用的事件检测算法；切换算法会显示该算法的常用参数。"
        )
        hint.setObjectName("aiHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(8)

        self._wave_algo_combo = QComboBox()
        self._wave_event_algos = available("event")
        for algo_name in self._wave_event_algos:
            self._wave_algo_combo.addItem(algo_name, algo_name)
        cur = self._settings.waveform_event_algo
        idx = self._wave_algo_combo.findData(cur)
        if idx < 0 and self._wave_event_algos:
            idx = 0
        if idx >= 0:
            self._wave_algo_combo.setCurrentIndex(idx)
        self._wave_algo_combo.setToolTip("kind=event 的算法自动列举；新增算法会自动出现")
        form.addRow("事件算法", self._wave_algo_combo)
        layout.addLayout(form)

        self._wave_param_form = QFormLayout()
        self._wave_param_form.setSpacing(8)
        param_box = QWidget()
        param_box.setLayout(self._wave_param_form)
        layout.addWidget(param_box)
        layout.addStretch(1)

        self._wave_param_editors: dict[str, QDoubleSpinBox | QSpinBox] = {}
        self._wave_get_algo = get
        self._wave_algo_combo.currentIndexChanged.connect(self._rebuild_wave_params)
        self._rebuild_wave_params()
        return tab

    def _rebuild_wave_params(self) -> None:
        """按当前所选算法的 params_cls 重建参数控件，回填已保存覆盖值。"""
        import dataclasses

        while self._wave_param_form.rowCount() > 0:
            self._wave_param_form.removeRow(0)
        self._wave_param_editors = {}

        algo_name = self._wave_algo_combo.currentData()
        if not algo_name:
            return
        try:
            instance = self._wave_get_algo(algo_name)
        except KeyError:
            return
        params_cls = getattr(instance, "params_cls", None)
        if params_cls is None:
            return

        saved = self._settings.waveform_algo_params.get(algo_name, {})
        for fld in dataclasses.fields(params_cls):
            default = saved.get(fld.name, fld.default)
            if fld.type in ("int", int):
                editor = QSpinBox()
                editor.setRange(0, 10_000_000)
                editor.setValue(int(default))
            else:
                editor = QDoubleSpinBox()
                editor.setDecimals(6)
                editor.setRange(0.0, 1_000_000.0)
                editor.setSingleStep(0.01)
                editor.setValue(float(default))
            editor.setToolTip(f"{fld.name}（默认 {fld.default}）")
            self._wave_param_form.addRow(fld.name, editor)
            self._wave_param_editors[fld.name] = editor

    def _build_whitelist_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        if self._policy is None:
            hint = QLabel("动作系统未就绪，白名单不可用。")
            hint.setObjectName("aiHint")
            layout.addWidget(hint)
            layout.addStretch(1)
            self._approve_list = None
            self._blocked_list = None
            return tab

        approve_hint = QLabel("常驻白名单（命中且护栏通过则免确认，重启仍生效）")
        approve_hint.setObjectName("aiHint")
        layout.addWidget(approve_hint)

        self._approve_list = QListWidget()
        self._approve_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self._approve_list, 1)

        approve_bar = QHBoxLayout()
        approve_bar.addStretch(1)
        remove_approve = QPushButton("移除所选")
        remove_approve.setAutoDefault(False)
        remove_approve.setDefault(False)
        remove_approve.clicked.connect(self._on_remove_approve)
        approve_bar.addWidget(remove_approve)
        layout.addLayout(approve_bar)

        blocked_hint = QLabel("黑名单（永远拒绝执行，优先级最高）")
        blocked_hint.setObjectName("aiHint")
        layout.addWidget(blocked_hint)

        self._blocked_list = QListWidget()
        self._blocked_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._blocked_list.setMaximumHeight(120)
        layout.addWidget(self._blocked_list)

        blocked_bar = QHBoxLayout()
        self._blocked_edit = QLineEdit()
        self._blocked_edit.setPlaceholderText("动作名，如 set_instrument_output")
        blocked_bar.addWidget(self._blocked_edit, 1)
        add_blocked = QPushButton("加入黑名单")
        add_blocked.setAutoDefault(False)
        add_blocked.setDefault(False)
        add_blocked.clicked.connect(self._on_add_blocked)
        blocked_bar.addWidget(add_blocked)
        remove_blocked = QPushButton("移除所选")
        remove_blocked.setAutoDefault(False)
        remove_blocked.setDefault(False)
        remove_blocked.clicked.connect(self._on_remove_blocked)
        blocked_bar.addWidget(remove_blocked)
        layout.addLayout(blocked_bar)

        self._reload_policy_lists()
        return tab

    def _reload_policy_lists(self) -> None:
        if self._policy is None:
            return
        self._approve_list.clear()
        for entry in self._policy.auto_approve:
            action = entry.get("action", "")
            when = entry.get("when") or {}
            text = action if not when else f"{action}  ·  {json.dumps(when, ensure_ascii=False)}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, entry)
            self._approve_list.addItem(item)
        self._blocked_list.clear()
        for name in self._policy.blocked:
            self._blocked_list.addItem(QListWidgetItem(str(name)))

    def _on_remove_approve(self) -> None:
        if self._policy is None:
            return
        row = self._approve_list.currentRow()
        if row < 0:
            return
        item = self._approve_list.item(row)
        entry = item.data(Qt.UserRole)
        try:
            self._policy.auto_approve.remove(entry)
        except ValueError:
            logger.warning("白名单条目已不存在: %s", entry)
        self._policy.save()
        self._reload_policy_lists()

    def _on_add_blocked(self) -> None:
        if self._policy is None:
            return
        name = self._blocked_edit.text().strip()
        if not name:
            return
        if name not in self._policy.blocked:
            self._policy.blocked.append(name)
            self._policy.save()
        self._blocked_edit.clear()
        self._reload_policy_lists()

    def _on_remove_blocked(self) -> None:
        if self._policy is None:
            return
        item = self._blocked_list.currentItem()
        if item is None:
            return
        name = item.text()
        if name in self._policy.blocked:
            self._policy.blocked.remove(name)
            self._policy.save()
        self._reload_policy_lists()

    def _build_experience_tab(self) -> QWidget:
        from core.ai.curator import Curator

        self._curator = Curator(self._settings)
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        regress_hint = QLabel("一键回归：用当前 prompt + 片段库跑全部 eval 用例")
        regress_hint.setObjectName("aiHint")
        layout.addWidget(regress_hint)

        regress_bar = QHBoxLayout()
        self._regress_btn = QPushButton("一键回归（mock）")
        self._regress_btn.setAutoDefault(False)
        self._regress_btn.setDefault(False)
        self._regress_btn.clicked.connect(self._on_run_eval)
        regress_bar.addWidget(self._regress_btn)
        self._regress_result = QLabel("")
        self._regress_result.setObjectName("aiHint")
        self._regress_result.setWordWrap(True)
        regress_bar.addWidget(self._regress_result, 1)
        layout.addLayout(regress_bar)

        exp_hint = QLabel("本机沉淀条目（纠偏 / 快捷指令 / eval 用例）")
        exp_hint.setObjectName("aiHint")
        layout.addWidget(exp_hint)

        self._exp_list = QListWidget()
        self._exp_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self._exp_list, 1)

        exp_bar = QHBoxLayout()
        remove_exp = QPushButton("删除所选")
        remove_exp.setAutoDefault(False)
        remove_exp.setDefault(False)
        remove_exp.clicked.connect(self._on_delete_experience)
        exp_bar.addWidget(remove_exp)
        exp_bar.addStretch(1)
        export_btn = QPushButton("导出经验包")
        export_btn.setAutoDefault(False)
        export_btn.setDefault(False)
        export_btn.clicked.connect(self._on_export_pack)
        exp_bar.addWidget(export_btn)
        reset_btn = QPushButton("重置为出厂")
        reset_btn.setAutoDefault(False)
        reset_btn.setDefault(False)
        reset_btn.clicked.connect(self._on_reset_local)
        exp_bar.addWidget(reset_btn)
        layout.addLayout(exp_bar)

        self._reload_experience_list()
        return tab

    def _reload_experience_list(self) -> None:
        self._exp_list.clear()
        data = self._curator.list_local()
        for item in data.get("nudges", []):
            entry = QListWidgetItem(f"[纠偏] {item.get('id')} · {item.get('when')}")
            entry.setData(Qt.UserRole, ("nudge", item.get("id")))
            self._exp_list.addItem(entry)
        for page_key, actions in (data.get("quick_actions") or {}).items():
            for action in actions:
                entry = QListWidgetItem(f"[快捷:{page_key}] {action}")
                entry.setData(Qt.UserRole, ("quick_action", None))
                self._exp_list.addItem(entry)
        for case_id in data.get("eval_cases", []):
            entry = QListWidgetItem(f"[eval] {case_id}")
            entry.setData(Qt.UserRole, ("eval_case", case_id))
            self._exp_list.addItem(entry)

    def _on_delete_experience(self) -> None:
        item = self._exp_list.currentItem()
        if item is None:
            return
        kind, ident = item.data(Qt.UserRole)
        if kind == "nudge" and ident:
            self._curator.delete_nudge(ident)
        elif kind == "eval_case" and ident:
            self._curator.delete_eval_case(ident)
        else:
            self._regress_result.setText("快捷指令请在快捷指令文件中删除。")
            return
        self._reload_experience_list()

    def _on_export_pack(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(
            self, "导出经验包", "kk_lab_ai_pack.zip", "Zip 文件 (*.zip)"
        )
        if not path:
            return
        if self._curator.export_pack(path):
            self._regress_result.setText(f"✓ 已导出：{path}")
        else:
            self._regress_result.setText("✗ 导出失败，请查看日志。")

    def _on_reset_local(self) -> None:
        confirm = QDialog(parent=self)
        confirm.setWindowTitle("确认重置")
        apply_ai_dialog_theme(confirm, _DIALOG_STYLE)
        c_layout = QVBoxLayout(confirm)
        c_layout.setContentsMargins(16, 16, 16, 16)
        c_layout.setSpacing(12)
        tip = QLabel("将清空用户层 prompt 与全部本机沉淀（保留随包项目层），不可恢复。继续？")
        tip.setWordWrap(True)
        c_layout.addWidget(tip)
        c_bar = QHBoxLayout()
        c_bar.addStretch(1)
        cancel = QPushButton("取消")
        cancel.setAutoDefault(True)
        cancel.setDefault(True)
        cancel.clicked.connect(confirm.reject)
        c_bar.addWidget(cancel)
        ok = QPushButton("确认重置")
        ok.setAutoDefault(False)
        ok.setDefault(False)
        ok.clicked.connect(confirm.accept)
        c_bar.addWidget(ok)
        c_layout.addLayout(c_bar)
        if not confirm.exec():
            return
        if self._curator.reset_local():
            self._regress_result.setText("✓ 已重置为出厂。")
        else:
            self._regress_result.setText("✗ 重置部分失败，请查看日志。")
        self._reload_experience_list()

    def _on_run_eval(self) -> None:
        from PySide6.QtCore import QObject, QThread, Signal

        from core.ai import eval_runner

        self._regress_btn.setEnabled(False)
        self._regress_result.setText("正在跑回归…")

        class _EvalWorker(QObject):
            done = Signal(int, int)
            failed = Signal(str)

            def run(self) -> None:
                try:
                    results = eval_runner.run_all(mock=True)
                    passed = sum(1 for r in results if r.passed)
                    self.done.emit(passed, len(results))
                except Exception as exc:  # noqa: BLE001
                    self.failed.emit(str(exc))

        thread = QThread(self)
        worker = _EvalWorker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(self._on_eval_done)
        worker.failed.connect(self._on_eval_failed)
        worker.done.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._eval_thread = thread
        self._eval_worker = worker
        thread.start()

    def _on_eval_done(self, passed: int, total: int) -> None:
        self._regress_btn.setEnabled(True)
        failed = total - passed
        color = "#7ee0a0" if failed == 0 else "#ff8a8a"
        self._regress_result.setText(f"通过 {passed} / 失败 {failed}（共 {total}）")
        self._regress_result.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _on_eval_failed(self, message: str) -> None:
        self._regress_btn.setEnabled(True)
        self._regress_result.setText(f"✗ 回归失败：{message}")
        self._regress_result.setStyleSheet("color: #ff8a8a; font-size: 11px;")

    def _build_button_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()

        self._test_btn = QPushButton("测试连接")
        self._test_btn.setAutoDefault(False)
        self._test_btn.setDefault(False)
        self._test_btn.clicked.connect(self._on_test_clicked)
        bar.addWidget(self._test_btn)

        self._probe_btn = QPushButton("探测模型")
        self._probe_btn.setAutoDefault(False)
        self._probe_btn.setDefault(False)
        self._probe_btn.setToolTip(
            "列出网关真实模型，并逐个实测流式/非流式下能否正常调用工具（tool_calls）"
        )
        self._probe_btn.clicked.connect(self._on_probe_clicked)
        bar.addWidget(self._probe_btn)

        bar.addStretch(1)

        cancel = QPushButton("取消")
        cancel.setAutoDefault(False)
        cancel.setDefault(False)
        cancel.clicked.connect(self.reject)
        bar.addWidget(cancel)

        ok = QPushButton("保存")
        ok.setObjectName("aiOkBtn")
        ok.setAutoDefault(True)
        ok.setDefault(True)
        ok.clicked.connect(self._on_save)
        bar.addWidget(ok)
        return bar

    def _on_mode_changed(self) -> None:
        """固定模式才需要默认模型；自动模式下置灰默认模型选择。"""
        self._model_combo.setEnabled(self._mode_combo.currentData() == "fixed")

    def _apply_to_settings(self) -> None:
        self._settings.enabled = self._enabled_chk.isChecked()
        self._settings.base_url = self._base_url_edit.text().strip()
        self._settings.api_key = self._api_key_edit.text().strip()
        self._settings.model_mode = self._mode_combo.currentData() or "fixed"
        self._settings.default_model = (
            self._model_combo.currentText().strip() or "deepseekv4flash"
        )
        models = [m.strip() for m in self._models_edit.text().split(",") if m.strip()]
        self._settings.available_models = models or ["deepseekv4flash", "glm-5.1-fp8"]
        self._settings.stream = self._stream_chk.isChecked()
        self._settings.timeout_seconds = int(self._timeout_spin.value())
        self._settings.max_recent_log_lines = int(self._log_lines_spin.value())
        self._settings.enable_log_masking = self._masking_chk.isChecked()
        self._settings.enable_history_summary = self._summary_chk.isChecked()
        self._settings.curator_ai_assist_enabled = self._curator_ai_chk.isChecked()
        self._settings.telemetry_enabled = self._telemetry_chk.isChecked()
        self._apply_waveform_settings()

    def _apply_waveform_settings(self) -> None:
        """把波形算法标签页的选择与参数写回 settings（仅存非默认覆盖值）。"""
        import dataclasses

        combo = getattr(self, "_wave_algo_combo", None)
        if combo is None:
            return
        algo_name = combo.currentData()
        if not algo_name:
            return
        self._settings.waveform_event_algo = algo_name
        try:
            instance = self._wave_get_algo(algo_name)
            params_cls = getattr(instance, "params_cls", None)
        except KeyError:
            params_cls = None
        overrides: dict[str, float] = {}
        if params_cls is not None:
            defaults = {f.name: f.default for f in dataclasses.fields(params_cls)}
            for name, editor in self._wave_param_editors.items():
                value = editor.value()
                if name in defaults and value != defaults[name]:
                    overrides[name] = value
        params_map = dict(self._settings.waveform_algo_params)
        if overrides:
            params_map[algo_name] = overrides
        else:
            params_map.pop(algo_name, None)
        self._settings.waveform_algo_params = params_map

    def _on_test_clicked(self) -> None:
        self._apply_to_settings()
        self._test_btn.setEnabled(False)
        self._test_result.setText("正在测试连接…")
        self._test_result.setStyleSheet("color: #c8d4ee;")
        self._service.test_connection()

    def _on_connection_tested(self, ok: bool, message: str) -> None:
        self._test_btn.setEnabled(True)
        self._probe_btn.setEnabled(True)
        if ok:
            self._test_result.setText(f"✓ {message}")
            self._test_result.setStyleSheet("color: #7ee0a0;")
        else:
            self._test_result.setText(f"✗ {message}")
            self._test_result.setStyleSheet("color: #ff8a8a;")

    def _on_probe_clicked(self) -> None:
        self._apply_to_settings()
        self._test_btn.setEnabled(False)
        self._probe_btn.setEnabled(False)
        self._test_result.setText("正在探测模型（逐个实测工具调用，稍候）…")
        self._test_result.setStyleSheet("color: #c8d4ee;")
        self._service.probe_models()

    def _on_models_probed(self, report: list) -> None:
        """展示探测结果：模型 → 非流式/流式 tool_calls 支持，并给出建议。

        同时把探测到的真实模型 id 回填「可选模型」清单，纠正别名不匹配问题。
        """
        self._test_btn.setEnabled(True)
        self._probe_btn.setEnabled(True)
        report = report or []
        models = [str(e.get("model", "")) for e in report if e.get("model")]
        if models:
            self._models_edit.setText(", ".join(models))
            cur = self._model_combo.currentText().strip()
            self._model_combo.clear()
            self._model_combo.addItems(models)
            self._model_combo.setCurrentText(cur or models[0])

        def mark(value) -> str:
            if value is True:
                return "✓"
            if value is False:
                return "✗"
            return "—"

        stream_on = self._stream_chk.isChecked()
        lines: list[str] = []
        recommended: list[str] = []
        for entry in report:
            model = str(entry.get("model", ""))
            ns = entry.get("tools_nostream")
            st = entry.get("tools_stream")
            err = entry.get("error") or ""
            line = f"{model}: 工具(非流式) {mark(ns)} · 工具(流式) {mark(st)}"
            if err:
                line += f" · {err}"
            lines.append(line)
            if (st if stream_on else ns) is True:
                recommended.append(model)

        text = "模型探测结果（当前流式=%s）：\n%s" % (
            "开" if stream_on else "关",
            "\n".join(lines) if lines else "（无模型）",
        )
        if recommended:
            text += "\n建议：当前流式设置下可正常调用工具的模型 → " + "、".join(recommended)
            self._test_result.setStyleSheet("color: #7ee0a0;")
        else:
            text += (
                "\n⚠ 当前流式设置下没有模型能正常返回 tool_calls，"
                "AI 将「只说不做」。请关闭流式，或改用上表「工具(流式) ✓」的模型。"
            )
            self._test_result.setStyleSheet("color: #ffcc66;")
        self._test_result.setText(text)

    def _on_save(self) -> None:
        self._apply_to_settings()
        if self._settings.save():
            try:
                self._service.start_telemetry()
            except Exception:
                logger.error("应用遥测开关失败", exc_info=True)
            self.accept()
        else:
            self._test_result.setText("✗ 保存配置失败，请检查日志")
            self._test_result.setStyleSheet("color: #ff8a8a;")
