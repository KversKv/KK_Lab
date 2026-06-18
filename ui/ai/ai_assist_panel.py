"""AIAssistPanel：右侧 AI 助手面板。

组成：标题栏 + ChatView + 输入框 + 发送/分析日志按钮。
通过 AIService 信号驱动 UI，自身不做阻塞 IO。
"""
from __future__ import annotations

import os
import sys

if __name__ == "__main__" and __package__ in (None, ""):
    _PROJECT_ROOT = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)

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
from ui.utils.icon_utils import tinted_svg_icon, tinted_svg_pixmap
from log_config import get_logger

logger = get_logger(__name__)

_AI_SVG_DIR = os.path.join(get_resource_base(), "resources", "icons_svg", "ai")
_SEND_ICON = os.path.join(_AI_SVG_DIR, "send.svg")
_PANEL_ICON = os.path.join(_AI_SVG_DIR, "ai_panel.svg")

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
    border: none;
}
QLabel#aiPanelTitleIcon {
    background: transparent;
    border: none;
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
    border: none;
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
        self._sequence_data_cb = None
        self._sequence_undo_cb = None
        self.setObjectName("aiAssistPanel")
        self.setStyleSheet(_PANEL_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        root.addLayout(self._build_header())

        self._chat = ChatView()
        root.addWidget(self._chat, 1)

        self._quick_row = self._build_quick_row()
        root.addWidget(self._quick_row)

        self._input = _InputEdit()
        self._input.setObjectName("aiInput")
        self._input.setPlaceholderText("Type a message. Enter to send / Shift+Enter for newline")
        self._input.setFixedHeight(72)
        self._input.submitted.connect(self._on_send_clicked)
        root.addWidget(self._input)

        root.addLayout(self._build_range_bar())
        root.addLayout(self._build_action_bar())
        root.addWidget(self._build_usage_bar())

        self._chat.add_system_message("AI Assistant is ready.")
        self._replay_history()
        self.refresh_quick_actions()
        self._wire_service()

    def _build_header(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        icon_label = QLabel()
        icon_label.setObjectName("aiPanelTitleIcon")
        icon_label.setFixedSize(16, 16)
        if os.path.isfile(_PANEL_ICON):
            icon_label.setPixmap(tinted_svg_pixmap(_PANEL_ICON, "#c6d4f2", 16))
        layout.addWidget(icon_label, 0, Qt.AlignVCenter)

        title = QLabel("AI Assistant")
        title.setObjectName("aiPanelTitle")
        layout.addWidget(title)
        layout.addStretch(1)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setObjectName("aiSettingsBtn")
        self._clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._clear_btn.setToolTip("Clear current conversation history")
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        layout.addWidget(self._clear_btn)

        self._settings_btn = QPushButton("Settings")
        self._settings_btn.setObjectName("aiSettingsBtn")
        self._settings_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        close_btn = QPushButton("×")
        close_btn.setObjectName("aiSettingsBtn")
        close_btn.setFixedWidth(28)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setToolTip("Close panel")
        close_btn.clicked.connect(self.request_close.emit)
        layout.addWidget(close_btn)
        return layout

    def _create_model_combo(self) -> QComboBox:
        self._model_combo = QComboBox()
        self._model_combo.setObjectName("aiModelCombo")
        self._model_combo.setToolTip("Switch model manually (auto by profile / pick a specific model)")
        self._model_combo.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self._model_combo.setMinimumWidth(120)
        self._populate_models()
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        return self._model_combo

    def _populate_models(self) -> None:
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.addItem("Auto (by page)", "")
        for model in self._service.available_models():
            self._model_combo.addItem(model, model)
        self._model_combo.setCurrentIndex(0)
        self._model_combo.blockSignals(False)

    def _on_model_changed(self, _text: str) -> None:
        model = self._model_combo.currentData() or ""
        self._service.set_model_override(model or None)
        if model:
            self._chat.add_system_message(f"Switched model: {model}")
        else:
            self._chat.add_system_message("Model reset to: Auto (by page)")

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

        level_label = QLabel("Log level")
        level_label.setObjectName("aiRangeLabel")
        layout.addWidget(level_label)

        self._level_combo = QComboBox()
        self._level_combo.setObjectName("aiLevelCombo")
        self._level_combo.addItems(_LOG_LEVELS)
        self._level_combo.setCurrentText("INFO")
        self._level_combo.setToolTip("Keep only logs at or above this level when analyzing")
        layout.addWidget(self._level_combo)

        lines_label = QLabel("Max lines")
        lines_label.setObjectName("aiRangeLabel")
        layout.addWidget(lines_label)

        self._lines_spin = QSpinBox()
        self._lines_spin.setObjectName("aiLinesSpin")
        self._lines_spin.setRange(20, _MAX_LINES_CAP)
        self._lines_spin.setSingleStep(50)
        self._lines_spin.setValue(300)
        self._lines_spin.setToolTip(f"Max lines kept per log category (cap {_MAX_LINES_CAP})")
        layout.addWidget(self._lines_spin)

        layout.addStretch(1)
        return layout

    def _build_action_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._analyze_btn = QPushButton("Analyze logs")
        self._analyze_btn.setObjectName("aiAnalyzeBtn")
        self._analyze_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._analyze_btn.setToolTip("Analyze based on recent run logs")
        self._analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self._analyze_btn)

        self._draft_btn = QPushButton("Generate draft")
        self._draft_btn.setObjectName("aiAnalyzeBtn")
        self._draft_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._draft_btn.setToolTip("Generate a test config/script draft from your input (applied only after preview & validation)")
        self._draft_btn.clicked.connect(self._on_draft_clicked)
        layout.addWidget(self._draft_btn)

        self._waveform_btn = QPushButton("Send waveform to AI")
        self._waveform_btn.setObjectName("aiAnalyzeBtn")
        self._waveform_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._waveform_btn.setToolTip("Send current page waveform (summary + downsampled) to AI for analysis")
        self._waveform_btn.clicked.connect(self._on_waveform_clicked)
        self._waveform_btn.setVisible(False)
        layout.addWidget(self._waveform_btn)

        layout.addStretch(1)

        layout.addWidget(self._create_model_combo())

        self._send_btn = QPushButton("Send")
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
        self._usage_label = QLabel("Usage (tokens): none")
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
            self._chat.add_system_message("No waveform data available on the current page.")
            return
        try:
            digest = self._waveform_provider_cb()
        except Exception:
            logger.error("获取波形摘要失败", exc_info=True)
            self._chat.add_system_message("Failed to get waveform data, please check the logs.")
            return
        if digest is None or not getattr(digest, "stats", None):
            self._chat.add_system_message("No waveform data available for analysis.")
            return
        text = self._input.toPlainText().strip() or "Please analyze the characteristics, anomalies and possible causes of the following waveform data."
        self._input.clear()
        self._chat.add_user_message(f"[Waveform] {text}")
        self._service.send_with_waveform(text, digest)

    def _on_usage_updated(self, turn, session) -> None:
        if turn is None:
            self._usage_label.setText("Usage (tokens): none")
            return
        try:
            tps = turn.output_tps
            sess_prompt = getattr(session, "prompt_tokens_total", 0)
            sess_completion = getattr(session, "completion_tokens_total", 0)
            requests = getattr(session, "requests", 0)
            self._usage_label.setText(
                f"This turn ↑{turn.prompt_tokens} ↓{turn.completion_tokens} tokens @ "
                f"{tps:.1f} tok·s⁻¹ ｜ Session ↑{sess_prompt} ↓{sess_completion} tokens"
                f" ({requests} requests)"
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
        self._chat.add_system_message("(Previous conversation history restored)")

    def _on_clear_clicked(self) -> None:
        self._service.clear_history()
        self._chat.add_system_message("Conversation history cleared.")

    def _on_stream_started(self) -> None:
        self._chat.begin_stream_message()

    def _on_stream_delta(self, chunk: str) -> None:
        self._chat.append_stream_delta(chunk)

    def _on_stream_finished(self, content: str) -> None:
        self._chat.end_stream_message(content)

    def confirm_action(self, spec, arguments: dict, reason: str = ""):
        """供 ActionDispatcher 注入的确认回调：弹 ActionConfirmDialog 二元确认。

        返回 ConfirmResult（含白名单写回意愿），由 dispatcher 据此落白名单（F2.4）。
        """
        from core.ai.actions import ConfirmResult
        from ui.ai.action_confirm_dialog import ActionConfirmDialog

        dialog = ActionConfirmDialog(
            action_name=spec.name,
            description=spec.description,
            risk_level=spec.risk_level,
            arguments=arguments,
            reason=reason,
            parent=self,
        )
        confirmed = dialog.exec() == QDialog.Accepted
        return ConfirmResult(
            confirmed=confirmed,
            remember_session=confirmed and dialog.remember_session,
            remember_resident=confirmed and dialog.remember_resident,
        )

    def _on_action_result(self, outcome) -> None:
        if outcome is None:
            return
        status = getattr(outcome, "status", "")
        name = getattr(outcome, "name", "")
        message = getattr(outcome, "message", "")
        prefix = {
            "executed": "✓ Executed",
            "denied": "⛔ Denied",
            "cancelled": "✗ Cancelled",
            "failed": "⚠ Failed",
        }.get(status, status)
        text = f"{prefix} action [{name}]"
        if message:
            text += f": {message}"
        self._chat.add_system_message(text)

    def set_config_apply_callback(self, callback) -> None:
        """注入测试配置草案 apply 回调：callback(ConfigDraft) -> (ok, message)。"""
        self._config_apply_cb = callback

    def set_script_apply_callback(self, callback) -> None:
        """注入测试脚本草案 apply 回调：callback(nodes) -> (ok, message)。"""
        self._script_apply_cb = callback

    def set_sequence_data_callback(self, callback) -> None:
        """注入当前画布序列读取回调：callback() -> v2 dict | None。

        用于脚本草案预览的 before/after diff（F5.4）。
        """
        self._sequence_data_cb = callback

    def set_sequence_undo_callback(self, callback) -> None:
        """注入序列撤销回调：callback() -> (ok, message)。

        应用草案后在聊天区给出"撤销 AI 修改"按钮（F5.5）。
        """
        self._sequence_undo_cb = callback

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
            f"Analyze recent logs (level ≥ {level}, ≤ {max_lines} lines each)"
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
            self._chat.add_system_message("Please describe the test config or script to generate in the input box first.")
            return
        kind = SCRIPT_DRAFT if self._script_apply_cb is not None else CONFIG_DRAFT
        label = "test script" if kind == SCRIPT_DRAFT else "test config"
        self._chat.add_user_message(f"Generate {label} draft: {text}")
        self._input.clear()
        self._service.generate_draft(kind, text)

    def _on_draft_ready(self, parsed: ParsedResponse) -> None:
        if parsed is None:
            return
        if not parsed.ok or parsed.payload is None:
            errors = "; ".join(parsed.errors) if parsed.errors else "Failed to parse draft"
            self._chat.add_system_message(f"Draft cannot be parsed: {errors}")
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
            self._chat.add_system_message("The current page does not support applying config drafts.")
            return
        from ui.ai.config_preview import ConfigPreviewDialog

        dialog = ConfigPreviewDialog(draft, self._config_apply_cb, parent=self)
        if dialog.exec():
            self._chat.add_system_message("Test config draft applied.")

    def _show_script_preview(self, draft) -> None:
        if self._script_apply_cb is None:
            self._chat.add_system_message("The current page does not support applying script drafts (switch to the Custom Test page).")
            return
        from ui.ai.script_preview import ScriptPreviewDialog

        before_sequence = None
        if self._sequence_data_cb is not None:
            try:
                before_sequence = self._sequence_data_cb()
            except Exception:
                logger.error("读取当前画布序列失败", exc_info=True)
                before_sequence = None

        dialog = ScriptPreviewDialog(
            draft,
            self._script_apply_cb,
            parent=self,
            before_sequence=before_sequence,
        )
        if dialog.exec():
            self._on_script_applied()

    def _on_script_applied(self) -> None:
        if self._sequence_undo_cb is None:
            self._chat.add_system_message("Test script draft applied to the canvas.")
            return

        def _undo() -> None:
            try:
                ok, message = self._sequence_undo_cb()
            except Exception:
                logger.error("撤销 AI 序列修改失败", exc_info=True)
                ok, message = False, "Undo failed, please check the logs."
            if ok:
                undo_btn.setEnabled(False)
                undo_btn.setText("Undone")
                self._chat.add_system_message("Reverted AI changes to the canvas.")
            else:
                self._chat.add_system_message(f"Undo failed: {message}")

        undo_btn = self._chat.add_system_action(
            "Test script draft applied to the canvas.", "Undo AI changes", _undo
        )

    def _on_response(self, content: str) -> None:
        self._chat.add_ai_message(content)

    def _on_analysis(self, result) -> None:
        self._chat.add_analysis_message(result)

    def _on_error(self, message: str) -> None:
        self._chat.add_system_message(f"Error: {message}")

    def _on_busy_changed(self, busy: bool) -> None:
        self._send_btn.setEnabled(not busy)
        self._analyze_btn.setEnabled(not busy)
        self._draft_btn.setEnabled(not busy)
        self._send_btn.setText("Processing…" if busy else "Send")

    def _on_connection_tested(self, ok: bool, message: str) -> None:
        if ok:
            self._chat.add_system_message(f"Connection test: {message}")
        else:
            self._chat.add_system_message(f"Connection test failed: {message}")

    def _open_settings(self) -> None:
        from ui.ai.ai_settings_dialog import AISettingsDialog

        dialog = AISettingsDialog(self._service, parent=self)
        if dialog.exec() == QDialog.Accepted:
            self._populate_models()


def _run_standalone() -> int:
    """独立运行 AI Assist 面板，便于脱离主窗口单独调试。"""
    from PySide6.QtWidgets import QApplication

    from core.ai.config import AISettings

    app = QApplication(sys.argv)

    settings = AISettings.load()
    service = AIService(settings)

    panel = AIAssistPanel(service)
    panel.setWindowTitle("AI Assistant (Standalone)")
    panel.resize(settings.panel_width or 360, 720)
    panel.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(_run_standalone())
