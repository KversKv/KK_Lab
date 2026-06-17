"""AISettingsDialog：AI 设置入口 + 「测试连接」。

遵守约定：parent=self；OK/Cancel/Test 按钮 default/autoDefault 显式二元化；
API Key 输入框用 EchoMode.Password，落盘走 AISettings.save（不展示 env 注入值）。
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from core.ai.ai_service import AIService
from log_config import get_logger

logger = get_logger(__name__)

_DIALOG_STYLE = """
QDialog { background-color: #0e1525; }
QLabel { color: #c8d4ee; font-size: 12px; background: transparent; }
QLineEdit, QSpinBox {
    background-color: #11182c; color: #e6eeff;
    border: 1px solid #243152; border-radius: 6px; padding: 4px 8px;
    min-height: 22px;
}
QCheckBox { color: #c8d4ee; font-size: 12px; }
QPushButton {
    min-height: 22px; padding: 4px 16px;
    border: 1px solid #22376A; border-radius: 8px;
    background-color: #13254b; color: #dce7ff; font-weight: 600; font-size: 12px;
}
QPushButton:hover { background-color: #1C2D55; border: 1px solid #3A5A9F; }
QPushButton#aiOkBtn { background-color: #5b3df5; border: 1px solid #6548ff; color: #ffffff; }
QLabel#aiTestResult { font-size: 11px; }
"""


class AISettingsDialog(QDialog):
    def __init__(self, service: AIService, parent=None):
        super().__init__(parent)
        self._service = service
        self._settings = service.settings
        self.setWindowTitle("AI 设置")
        self.setMinimumWidth(440)
        self.setStyleSheet(_DIALOG_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

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

        self._model_edit = QLineEdit(self._settings.default_model)
        self._model_edit.setPlaceholderText("glm-5.1-fp8")
        form.addRow("默认模型", self._model_edit)

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

        root.addLayout(form)

        self._test_result = QLabel("")
        self._test_result.setObjectName("aiTestResult")
        self._test_result.setWordWrap(True)
        root.addWidget(self._test_result)

        root.addLayout(self._build_button_bar())

        self._service.connection_tested.connect(self._on_connection_tested)

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

    def _apply_to_settings(self) -> None:
        self._settings.enabled = self._enabled_chk.isChecked()
        self._settings.base_url = self._base_url_edit.text().strip()
        self._settings.api_key = self._api_key_edit.text().strip()
        self._settings.default_model = self._model_edit.text().strip() or "glm-5.1-fp8"
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
