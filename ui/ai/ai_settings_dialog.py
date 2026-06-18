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

logger = get_logger(__name__)

_DIALOG_STYLE = """
QDialog { background-color: #0e1525; }
QLabel { color: #c8d4ee; font-size: 12px; background: transparent; }
QLineEdit, QSpinBox, QComboBox {
    background-color: #11182c; color: #e6eeff;
    border: 1px solid #243152; border-radius: 6px; padding: 4px 8px;
    min-height: 22px;
}
QComboBox::drop-down { border: none; width: 18px; }
QComboBox QAbstractItemView {
    background-color: #11182c; color: #dce7ff;
    border: 1px solid #243152; selection-background-color: #1C2D55;
}
QCheckBox { color: #c8d4ee; font-size: 12px; }
QListWidget {
    background-color: #11182c; color: #dce7ff;
    border: 1px solid #243152; border-radius: 6px;
    font-size: 11px;
}
QListWidget::item { padding: 4px 6px; }
QListWidget::item:selected { background-color: #1C2D55; }
QTabWidget::pane { border: 1px solid #243152; border-radius: 8px; top: -1px; }
QTabBar::tab {
    background-color: #11182c; color: #9fb2d8;
    border: 1px solid #243152; border-bottom: none;
    padding: 5px 16px; margin-right: 2px;
    border-top-left-radius: 8px; border-top-right-radius: 8px;
    font-size: 12px;
}
QTabBar::tab:selected { background-color: #1C2D55; color: #eaf1ff; }
QPushButton {
    min-height: 22px; padding: 4px 16px;
    border: 1px solid #22376A; border-radius: 8px;
    background-color: #13254b; color: #dce7ff; font-weight: 600; font-size: 12px;
}
QPushButton:hover { background-color: #1C2D55; border: 1px solid #3A5A9F; }
QPushButton#aiOkBtn { background-color: #5b3df5; border: 1px solid #6548ff; color: #ffffff; }
QLabel#aiTestResult { font-size: 11px; }
QLabel#aiHint { color: #8fa0c4; font-size: 11px; }
"""


class AISettingsDialog(QDialog):
    def __init__(self, service: AIService, parent=None):
        super().__init__(parent)
        self._service = service
        self._settings = service.settings
        self._policy = service.dispatcher.policy if service.dispatcher else None
        self.setWindowTitle("AI 设置")
        self.setMinimumWidth(460)
        self.setStyleSheet(_DIALOG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "常规")
        tabs.addTab(self._build_whitelist_tab(), "白名单")
        root.addWidget(tabs)

        self._test_result = QLabel("")
        self._test_result.setObjectName("aiTestResult")
        self._test_result.setWordWrap(True)
        root.addWidget(self._test_result)

        root.addLayout(self._build_button_bar())

        self._service.connection_tested.connect(self._on_connection_tested)

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

        layout.addLayout(form)
        layout.addStretch(1)
        return tab

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

    def _build_button_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()

        self._test_btn = QPushButton("测试连接")
        self._test_btn.setAutoDefault(False)
        self._test_btn.setDefault(False)
        self._test_btn.clicked.connect(self._on_test_clicked)
        bar.addWidget(self._test_btn)

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

    def _on_test_clicked(self) -> None:
        self._apply_to_settings()
        self._test_btn.setEnabled(False)
        self._test_result.setText("正在测试连接…")
        self._test_result.setStyleSheet("color: #c8d4ee;")
        self._service.test_connection()

    def _on_connection_tested(self, ok: bool, message: str) -> None:
        self._test_btn.setEnabled(True)
        if ok:
            self._test_result.setText(f"✓ {message}")
            self._test_result.setStyleSheet("color: #7ee0a0;")
        else:
            self._test_result.setText(f"✗ {message}")
            self._test_result.setStyleSheet("color: #ff8a8a;")

    def _on_save(self) -> None:
        self._apply_to_settings()
        if self._settings.save():
            self.accept()
        else:
            self._test_result.setText("✗ 保存配置失败，请检查日志")
            self._test_result.setStyleSheet("color: #ff8a8a;")
