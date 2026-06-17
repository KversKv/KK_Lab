"""AIAssistPanel：右侧 AI 助手面板。

组成：标题栏 + ChatView + 输入框 + 发送/分析日志按钮。
通过 AIService 信号驱动 UI，自身不做阻塞 IO。
"""
from __future__ import annotations

import os

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.ai.ai_service import AIService
from core.ai.context_builder import ContextOptions
from core.ai.profiles import get_quick_actions
from core.ai.response_parser import ParsedResponse
from core.ai.schemas import CONFIG_DRAFT, SCRIPT_DRAFT
from ui.ai.chat_view import ChatView
from ui.resource_path import get_resource_base
from ui.utils.icon_utils import tinted_svg_icon
from log_config import get_logger

logger = get_logger(__name__)

_AI_SVG_DIR = os.path.join(get_resource_base(), "resources", "icons_svg", "ai")
_SEND_ICON = os.path.join(_AI_SVG_DIR, "send.svg")

_PANEL_STYLE = """
QFrame#aiAssistPanel {
    background-color: #0b1020;
    border-left: 1px solid #1a2440;
}
QLabel#aiPanelTitle {
    color: #d7e3ff;
    font-size: 13px;
    font-weight: 700;
    background: transparent;
}
QPlainTextEdit#aiInput {
    background-color: #11182c;
    color: #e6eeff;
    border: 1px solid #243152;
    border-radius: 8px;
    padding: 6px 8px;
    font-size: 12px;
}
QPushButton#aiSendBtn, QPushButton#aiAnalyzeBtn, QPushButton#aiSettingsBtn {
    min-height: 22px;
    padding: 2px 10px;
    border: 1px solid #22376A;
    border-radius: 8px;
    background-color: #13254b;
    color: #dce7ff;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#aiSendBtn:hover, QPushButton#aiAnalyzeBtn:hover, QPushButton#aiSettingsBtn:hover {
    background-color: #1C2D55;
    border: 1px solid #3A5A9F;
}
QPushButton#aiSendBtn:disabled, QPushButton#aiAnalyzeBtn:disabled {
    background-color: #0b1430;
    color: #5c7096;
    border: 1px solid #1a2850;
}
QLabel#aiRangeLabel {
    color: #8fa3c2;
    font-size: 11px;
    background: transparent;
}
QComboBox#aiLevelCombo {
    min-height: 22px;
    padding: 1px 6px;
    border: 1px solid #243152;
    border-radius: 6px;
    background-color: #11182c;
    color: #dce7ff;
    font-size: 11px;
}
QComboBox#aiLevelCombo QAbstractItemView {
    background-color: #11182c;
    color: #dce7ff;
    selection-background-color: #1d3a6e;
}
QSpinBox#aiLinesSpin {
    min-height: 22px;
    padding: 1px 4px;
    border: 1px solid #243152;
    border-radius: 6px;
    background-color: #11182c;
    color: #dce7ff;
    font-size: 11px;
}
QComboBox#aiModelCombo {
    min-height: 22px;
    padding: 1px 6px;
    border: 1px solid #243152;
    border-radius: 6px;
    background-color: #11182c;
    color: #dce7ff;
    font-size: 11px;
}
QComboBox#aiModelCombo QAbstractItemView {
    background-color: #11182c;
    color: #dce7ff;
    selection-background-color: #1d3a6e;
}
QPushButton#aiQuickBtn {
    min-height: 22px;
    padding: 1px 10px;
    border: 1px solid #22376A;
    border-radius: 11px;
    background-color: #101b38;
    color: #b9cbf0;
    font-size: 11px;
}
QPushButton#aiQuickBtn:hover {
    background-color: #1C2D55;
    border: 1px solid #3A5A9F;
}
QLabel#aiUsageLabel {
    color: #7e93b8;
    font-size: 10px;
    background: transparent;
    padding: 1px 2px;
}
"""

_LOG_LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")
_MAX_LINES_CAP = 1000


class _InputEdit(QPlainTextEdit):
    """Enter 发送，Shift+Enter 换行。"""

    submitted = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (
            event.modifiers() & Qt.ShiftModifier
        ):
            self.submitted.emit()
            return
        super().keyPressEvent(event)


class AIAssistPanel(QFrame):
    request_close = Signal()

    def __init__(self, service: AIService, parent=None):
        super().__init__(parent)
        self._service = service
        self._config_apply_cb = None
        self._script_apply_cb = None
        self._waveform_provider_cb = None
        self.setObjectName("aiAssistPanel")
        self.setStyleSheet(_PANEL_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addLayout(self._build_header())
        root.addLayout(self._build_model_bar())

        self._chat = ChatView()
        root.addWidget(self._chat, 1)

        self._quick_row = self._build_quick_row()
        root.addWidget(self._quick_row)

        self._input = _InputEdit()
        self._input.setObjectName("aiInput")
        self._input.setPlaceholderText("输入问题，Enter 发送 / Shift+Enter 换行")
        self._input.setFixedHeight(72)
        self._input.submitted.connect(self._on_send_clicked)
        root.addWidget(self._input)

        root.addLayout(self._build_range_bar())
        root.addLayout(self._build_action_bar())
        root.addWidget(self._build_usage_bar())

        self._chat.add_system_message("AI 助手已就绪。")
        self._replay_history()
        self.refresh_quick_actions()
        self._wire_service()

    def _build_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("AI 助手")
        title.setObjectName("aiPanelTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        self._clear_btn = QPushButton("清空")
        self._clear_btn.setObjectName("aiSettingsBtn")
        self._clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._clear_btn.setToolTip("清空当前会话历史")
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        layout.addWidget(self._clear_btn)

        self._settings_btn = QPushButton("设置")
        self._settings_btn.setObjectName("aiSettingsBtn")
        self._settings_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("aiSettingsBtn")
        close_btn.setFixedWidth(28)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setToolTip("关闭面板")
        close_btn.clicked.connect(self.request_close.emit)
        layout.addWidget(close_btn)
        return layout

    def _build_model_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        model_label = QLabel("模型")
        model_label.setObjectName("aiRangeLabel")
        layout.addWidget(model_label)

        self._model_combo = QComboBox()
        self._model_combo.setObjectName("aiModelCombo")
        self._model_combo.setToolTip("手动切换模型（按 Profile 自动选择 / 指定模型）")
        self._populate_models()
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self._model_combo, 1)
        return layout

    def _populate_models(self) -> None:
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.addItem("自动（按页面）", "")
        for model in self._service.available_models():
            self._model_combo.addItem(model, model)
        self._model_combo.setCurrentIndex(0)
        self._model_combo.blockSignals(False)

    def _on_model_changed(self, _text: str) -> None:
        model = self._model_combo.currentData() or ""
        self._service.set_model_override(model or None)
        if model:
            self._chat.add_system_message(f"已切换模型：{model}")
        else:
            self._chat.add_system_message("模型已切回：自动（按页面）")

    def _build_quick_row(self) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addStretch(1)
        self._quick_layout = layout
        return row

    def refresh_quick_actions(self) -> None:
        """按当前页面 Profile 重建快捷指令按钮（5.4）。"""
        layout = getattr(self, "_quick_layout", None)
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        actions = get_quick_actions(self._service.current_page_key())
        for text in actions:
            btn = QPushButton(text)
            btn.setObjectName("aiQuickBtn")
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _checked=False, t=text: self._on_quick_clicked(t))
            layout.addWidget(btn)
        layout.addStretch(1)
        self._quick_row.setVisible(bool(actions))

    def _on_quick_clicked(self, text: str) -> None:
        self._input.setPlainText(text)
        self._on_send_clicked()

    def _build_range_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        level_label = QLabel("日志等级")
        level_label.setObjectName("aiRangeLabel")
        layout.addWidget(level_label)

        self._level_combo = QComboBox()
        self._level_combo.setObjectName("aiLevelCombo")
        self._level_combo.addItems(_LOG_LEVELS)
        self._level_combo.setCurrentText("INFO")
        self._level_combo.setToolTip("分析时只保留不低于该等级的日志")
        layout.addWidget(self._level_combo)

        lines_label = QLabel("最大行数")
        lines_label.setObjectName("aiRangeLabel")
        layout.addWidget(lines_label)

        self._lines_spin = QSpinBox()
        self._lines_spin.setObjectName("aiLinesSpin")
        self._lines_spin.setRange(20, _MAX_LINES_CAP)
        self._lines_spin.setSingleStep(50)
        self._lines_spin.setValue(300)
        self._lines_spin.setToolTip(f"每类日志取的最大行数（上限 {_MAX_LINES_CAP}）")
        layout.addWidget(self._lines_spin)

        layout.addStretch(1)
        return layout

    def _build_action_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._analyze_btn = QPushButton("分析日志")
        self._analyze_btn.setObjectName("aiAnalyzeBtn")
        self._analyze_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._analyze_btn.setToolTip("基于最近运行日志进行分析")
        self._analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self._analyze_btn)

        self._draft_btn = QPushButton("生成草案")
        self._draft_btn.setObjectName("aiAnalyzeBtn")
        self._draft_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._draft_btn.setToolTip("根据输入框需求生成测试配置/脚本草案（预览校验后才应用）")
        self._draft_btn.clicked.connect(self._on_draft_clicked)
        layout.addWidget(self._draft_btn)

        self._waveform_btn = QPushButton("发送波形给 AI")
        self._waveform_btn.setObjectName("aiAnalyzeBtn")
        self._waveform_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._waveform_btn.setToolTip("把当前页面波形（摘要+降采样）发送给 AI 分析")
        self._waveform_btn.clicked.connect(self._on_waveform_clicked)
        self._waveform_btn.setVisible(False)
        layout.addWidget(self._waveform_btn)

        layout.addStretch(1)

        self._send_btn = QPushButton("发送")
        self._send_btn.setObjectName("aiSendBtn")
        self._send_btn.setCursor(QCursor(Qt.PointingHandCursor))
        if os.path.isfile(_SEND_ICON):
            self._send_btn.setIcon(tinted_svg_icon(_SEND_ICON, "#dce7ff", 14))
            self._send_btn.setIconSize(QSize(14, 14))
        self._send_btn.clicked.connect(self._on_send_clicked)
        layout.addWidget(self._send_btn)
        return layout

    def _build_usage_bar(self) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._usage_label = QLabel("用量 (tokens)：暂无")
        self._usage_label.setObjectName("aiUsageLabel")
        self._usage_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._usage_label)
        layout.addStretch(1)
        return row

    def set_waveform_provider_callback(self, callback) -> None:
        """注入波形提供回调：callback() -> WaveformDigest | None。

        传入 None 表示当前页面无波形源，隐藏"发送波形给 AI"按钮。
        """
        self._waveform_provider_cb = callback
        if hasattr(self, "_waveform_btn"):
            self._waveform_btn.setVisible(callback is not None)

    def _on_waveform_clicked(self) -> None:
        if self._waveform_provider_cb is None:
            self._chat.add_system_message("当前页面无可发送的波形数据。")
            return
        try:
            digest = self._waveform_provider_cb()
        except Exception:
            logger.error("获取波形摘要失败", exc_info=True)
            self._chat.add_system_message("获取波形数据失败，请查看日志。")
            return
        if digest is None or not getattr(digest, "stats", None):
            self._chat.add_system_message("当前没有可分析的波形数据。")
            return
        text = self._input.toPlainText().strip() or "请分析以下波形数据的特征、异常与可能原因。"
        self._input.clear()
        self._chat.add_user_message(f"[发送波形] {text}")
        self._service.send_with_waveform(text, digest)

    def _on_usage_updated(self, turn, session) -> None:
        if turn is None:
            self._usage_label.setText("用量 (tokens)：暂无")
            return
        try:
            tps = turn.output_tps
            sess_prompt = getattr(session, "prompt_tokens_total", 0)
            sess_completion = getattr(session, "completion_tokens_total", 0)
            requests = getattr(session, "requests", 0)
            self._usage_label.setText(
                f"本次 ↑{turn.prompt_tokens} ↓{turn.completion_tokens} tokens @ "
                f"{tps:.1f} tok·s⁻¹ ｜ 会话 ↑{sess_prompt} ↓{sess_completion} tokens"
                f"（{requests} 次）"
            )
        except Exception:
            logger.error("刷新用量状态栏失败", exc_info=True)

    def _wire_service(self) -> None:
        self._service.response_ready.connect(self._on_response)
        self._service.response_started.connect(self._on_stream_started)
        self._service.response_delta.connect(self._on_stream_delta)
        self._service.response_finished.connect(self._on_stream_finished)
        self._service.analysis_ready.connect(self._on_analysis)
        self._service.draft_ready.connect(self._on_draft_ready)
        self._service.error_occurred.connect(self._on_error)
        self._service.busy_changed.connect(self._on_busy_changed)
        self._service.connection_tested.connect(self._on_connection_tested)
        self._service.action_result.connect(self._on_action_result)
        self._service.usage_updated.connect(self._on_usage_updated)

    def _replay_history(self) -> None:
        """启动时回放持久化的会话历史（5.2）。"""
        history = self._service.persisted_history()
        if not history:
            return
        for item in history:
            role = item.get("role")
            content = item.get("content") or ""
            if role == "user":
                self._chat.add_user_message(content)
            elif role == "assistant":
                self._chat.add_ai_message(content)
        self._chat.add_system_message("（已恢复上次会话历史）")

    def _on_clear_clicked(self) -> None:
        self._service.clear_history()
        self._chat.add_system_message("会话历史已清空。")

    def _on_stream_started(self) -> None:
        self._chat.begin_stream_message()

    def _on_stream_delta(self, chunk: str) -> None:
        self._chat.append_stream_delta(chunk)

    def _on_stream_finished(self, content: str) -> None:
        self._chat.end_stream_message(content)

    def confirm_action(self, spec, arguments: dict, reason: str = "") -> bool:
        """供 ActionDispatcher 注入的确认回调：弹 ActionConfirmDialog 二元确认。"""
        from ui.ai.action_confirm_dialog import ActionConfirmDialog

        dialog = ActionConfirmDialog(
            action_name=spec.name,
            description=spec.description,
            risk_level=spec.risk_level,
            arguments=arguments,
            reason=reason,
            parent=self,
        )
        return dialog.exec() == QDialog.Accepted

    def _on_action_result(self, outcome) -> None:
        if outcome is None:
            return
        status = getattr(outcome, "status", "")
        name = getattr(outcome, "name", "")
        message = getattr(outcome, "message", "")
        prefix = {
            "executed": "✓ 已执行",
            "denied": "⛔ 已拒绝",
            "cancelled": "✗ 已取消",
            "failed": "⚠ 执行失败",
        }.get(status, status)
        text = f"{prefix} 动作 [{name}]"
        if message:
            text += f"：{message}"
        self._chat.add_system_message(text)

    def set_config_apply_callback(self, callback) -> None:
        """注入测试配置草案 apply 回调：callback(ConfigDraft) -> (ok, message)。"""
        self._config_apply_cb = callback

    def set_script_apply_callback(self, callback) -> None:
        """注入测试脚本草案 apply 回调：callback(nodes) -> (ok, message)。"""
        self._script_apply_cb = callback

    def _on_send_clicked(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._chat.add_user_message(text)
        self._input.clear()
        self._service.send(text)

    def _on_analyze_clicked(self) -> None:
        level = self._level_combo.currentText()
        max_lines = min(self._lines_spin.value(), _MAX_LINES_CAP)
        self._chat.add_user_message(
            f"分析最近日志（等级≥{level}，每类≤{max_lines}行）"
        )
        options = ContextOptions(
            max_app_lines=max_lines,
            max_exec_lines=max_lines,
            max_rx_lines=max_lines,
            min_level=level,
            enable_masking=self._service.settings.enable_log_masking,
        )
        self._service.analyze_logs(options)

    def _on_draft_clicked(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            self._chat.add_system_message("请先在输入框描述需要生成的测试配置或脚本。")
            return
        kind = SCRIPT_DRAFT if self._script_apply_cb is not None else CONFIG_DRAFT
        label = "测试脚本" if kind == SCRIPT_DRAFT else "测试配置"
        self._chat.add_user_message(f"生成{label}草案：{text}")
        self._input.clear()
        self._service.generate_draft(kind, text)

    def _on_draft_ready(self, parsed: ParsedResponse) -> None:
        if parsed is None:
            return
        if not parsed.ok or parsed.payload is None:
            errors = "；".join(parsed.errors) if parsed.errors else "草案解析失败"
            self._chat.add_system_message(f"草案无法解析：{errors}")
            if parsed.message:
                self._chat.add_ai_message(parsed.message)
            return
        if parsed.kind == SCRIPT_DRAFT:
            self._show_script_preview(parsed.payload)
        elif parsed.kind == CONFIG_DRAFT:
            self._show_config_preview(parsed.payload)
        else:
            self._chat.add_ai_message(parsed.message or parsed.raw)

    def _show_config_preview(self, draft) -> None:
        if self._config_apply_cb is None:
            self._chat.add_system_message("当前页面不支持应用配置草案。")
            return
        from ui.ai.config_preview import ConfigPreviewDialog

        dialog = ConfigPreviewDialog(draft, self._config_apply_cb, parent=self)
        if dialog.exec():
            self._chat.add_system_message("已应用测试配置草案。")

    def _show_script_preview(self, draft) -> None:
        if self._script_apply_cb is None:
            self._chat.add_system_message("当前页面不支持应用脚本草案（请切到 Custom Test 页面）。")
            return
        from ui.ai.script_preview import ScriptPreviewDialog

        dialog = ScriptPreviewDialog(draft, self._script_apply_cb, parent=self)
        if dialog.exec():
            self._chat.add_system_message("已将测试脚本草案应用到画布。")

    def _on_response(self, content: str) -> None:
        self._chat.add_ai_message(content)

    def _on_analysis(self, result) -> None:
        self._chat.add_analysis_message(result)

    def _on_error(self, message: str) -> None:
        self._chat.add_system_message(f"错误：{message}")

    def _on_busy_changed(self, busy: bool) -> None:
        self._send_btn.setEnabled(not busy)
        self._analyze_btn.setEnabled(not busy)
        self._draft_btn.setEnabled(not busy)
        self._send_btn.setText("处理中…" if busy else "发送")

    def _on_connection_tested(self, ok: bool, message: str) -> None:
        if ok:
            self._chat.add_system_message(f"测试连接：{message}")
        else:
            self._chat.add_system_message(f"测试连接失败：{message}")

    def _open_settings(self) -> None:
        from ui.ai.ai_settings_dialog import AISettingsDialog

        dialog = AISettingsDialog(self._service, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._populate_models()
