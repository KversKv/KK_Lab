"""AIAssistPanel：右侧 AI 助手面板。

组成：标题栏 + ChatView + 输入框 + 发送/分析日志按钮。
通过 AIService 信号驱动 UI，自身不做阻塞 IO。
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QEasingCurve,
    QEventLoop,
    QObject,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
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

if TYPE_CHECKING:
    from core.ai.actions.dispatcher import ConfirmResult

logger = get_logger(__name__)

_AI_SVG_DIR = os.path.join(get_resource_base(), "resources", "icons_svg", "ai")
_SEND_ICON = os.path.join(_AI_SVG_DIR, "send.svg")
_PANEL_ICON = os.path.join(_AI_SVG_DIR, "ai_panel.svg")
_SPARKLES_ICON = os.path.join(_AI_SVG_DIR, "sparkles.svg")

_PANEL_STYLE = """
QFrame#aiAssistPanel {
    background-color: #070709;
    border-left: 1px solid #1e293b;
}
QFrame#aiHeaderBar {
    background-color: #020617;
    border-bottom: 1px solid #1e293b;
}
QFrame#aiBottomBar {
    background-color: #070709;
    border-top: 1px solid #1e293b;
}
QLabel#aiPanelTitle {
    color: #e2e8f0;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.4px;
    background: transparent;
    border: none;
}
QLabel#aiPanelTitleIcon {
    background: transparent;
    border: none;
}
QLabel#aiHeaderSep {
    color: #1e293b;
    font-size: 14px;
    background: transparent;
    border: none;
}
QPushButton#aiSettingsBtn {
    min-height: 22px;
    padding: 4px 10px;
    border: none;
    border-radius: 6px;
    background-color: #1e293b;
    color: #cbd5e1;
    font-size: 12px;
    font-weight: 600;
}
QPushButton#aiSettingsBtn:hover {
    background-color: #334155;
    color: #e2e8f0;
}
QPushButton#aiCloseBtn {
    border: none;
    border-radius: 6px;
    background-color: transparent;
    color: #64748b;
    font-size: 16px;
    font-weight: 700;
}
QPushButton#aiCloseBtn:hover {
    background-color: #1e293b;
    color: #e2e8f0;
}
QPlainTextEdit#aiInput {
    background-color: #070709;
    color: #e2e8f0;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 8px 10px;
    font-size: 12px;
}
QPlainTextEdit#aiInput:focus {
    border: 1px solid #3b82f6;
}
QPushButton#aiSendBtn {
    min-height: 22px;
    padding: 4px 14px;
    border: none;
    border-radius: 4px;
    background-color: #2563eb;
    color: #ffffff;
    font-size: 11px;
    font-weight: 700;
}
QPushButton#aiSendBtn:hover {
    background-color: #1d4fd0;
}
QPushButton#aiSendBtn:disabled {
    background-color: #0f172a;
    color: #475569;
}
QPushButton#aiAnalyzeBtn {
    min-height: 22px;
    padding: 4px 12px;
    border: 1px solid #1d2f52;
    border-radius: 8px;
    background-color: #0e1b33;
    color: #3b82f6;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#aiAnalyzeBtn:hover {
    background-color: #14264a;
}
QPushButton#aiAnalyzeBtn:disabled {
    background-color: #0f172a;
    color: #475569;
    border: 1px solid #1e293b;
}
QPushButton#aiScriptBtn {
    min-height: 22px;
    padding: 4px 12px;
    border: 1px solid #2a2750;
    border-radius: 8px;
    background-color: #171430;
    color: #818cf8;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#aiScriptBtn:hover {
    background-color: #211d44;
}
QPushButton#aiScriptBtn:disabled {
    background-color: #0f172a;
    color: #475569;
    border: 1px solid #1e293b;
}
QLabel#aiRangeLabel {
    color: #64748b;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.4px;
    background: transparent;
}
QComboBox#aiLevelCombo {
    min-height: 22px;
    padding: 1px 6px;
    border: 1px solid #1e293b;
    border-radius: 4px;
    background-color: #0f172a;
    color: #cbd5e1;
    font-size: 10px;
    font-weight: 700;
}
QComboBox#aiLevelCombo QAbstractItemView {
    background-color: #0f172a;
    color: #cbd5e1;
    selection-background-color: #1d3a6e;
}
QSpinBox#aiLinesSpin {
    min-height: 22px;
    padding: 1px 4px;
    border: 1px solid #1e293b;
    border-radius: 4px;
    background-color: #0f172a;
    color: #cbd5e1;
    font-size: 10px;
    font-weight: 700;
}
QComboBox#aiModelCombo {
    min-height: 22px;
    padding: 1px 6px;
    border: 1px solid #1e293b;
    border-radius: 4px;
    background-color: transparent;
    color: #cbd5e1;
    font-size: 10px;
    font-weight: 700;
}
QComboBox#aiModelCombo:hover {
    border: 1px solid #334155;
}
QComboBox#aiModelCombo QAbstractItemView {
    background-color: #0f172a;
    color: #cbd5e1;
    selection-background-color: #1d3a6e;
}
QPushButton#aiQuickBtn {
    min-height: 22px;
    padding: 5px 12px;
    border: 1px solid #1e293b;
    border-radius: 8px;
    background-color: #0f172a;
    color: #94a3b8;
    font-size: 10px;
    font-weight: 700;
}
QPushButton#aiQuickBtn:hover {
    background-color: #1e293b;
    color: #cbd5e1;
}
QLabel#aiUsageLabel {
    color: #64748b;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.4px;
    background: transparent;
    padding: 1px 2px;
}
"""

_LOG_LEVELS = ("DEBUG", "INFO", "WARN", "ERROR")
_MAX_LINES_CAP = 1000


class _InputEdit(QPlainTextEdit):
    """Enter 发送，Shift+Enter 换行；聚焦时显示蓝色焦点环，高度随内容弹性自适应。"""

    submitted = Signal()

    _MIN_HEIGHT = 80
    _MAX_HEIGHT = 160

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFixedHeight(self._MIN_HEIGHT)

        self._focus_ring = QGraphicsDropShadowEffect(self)
        self._focus_ring.setColor(QColor(59, 130, 246, 90))
        self._focus_ring.setBlurRadius(14)
        self._focus_ring.setOffset(0, 0)
        self._focus_ring.setEnabled(False)
        self.setGraphicsEffect(self._focus_ring)

        self.document().documentLayout().documentSizeChanged.connect(
            self._adjust_height
        )

    def _adjust_height(self) -> None:
        doc_height = int(self.document().size().height())
        target = max(self._MIN_HEIGHT, min(self._MAX_HEIGHT, doc_height + 18))
        if target != self.height():
            self.setFixedHeight(target)

    def focusInEvent(self, event) -> None:
        self._focus_ring.setEnabled(True)
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._focus_ring.setEnabled(False)
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (
            event.modifiers() & Qt.ShiftModifier
        ):
            self.submitted.emit()
            return
        super().keyPressEvent(event)


class _PressScaleButton(QPushButton):
    """按下时几何缩放至 95%、松开还原的微动效按钮（active:scale-95）。"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(90)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._base_geometry: QRect | None = None

    def _scaled_rect(self, factor: float) -> QRect:
        rect = self._base_geometry or self.geometry()
        new_w = int(rect.width() * factor)
        new_h = int(rect.height() * factor)
        dx = (rect.width() - new_w) // 2
        dy = (rect.height() - new_h) // 2
        return QRect(rect.x() + dx, rect.y() + dy, new_w, new_h)

    def mousePressEvent(self, event) -> None:
        self._base_geometry = self.geometry()
        self._anim.stop()
        self._anim.setStartValue(self.geometry())
        self._anim.setEndValue(self._scaled_rect(0.95))
        self._anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._base_geometry is not None:
            self._anim.stop()
            self._anim.setStartValue(self.geometry())
            self._anim.setEndValue(self._base_geometry)
            self._anim.start()
        super().mouseReleaseEvent(event)


class _DigestWorker(QObject):
    """后台线程构建波形摘要，避免在 UI 主线程做百万点级 CPU 计算导致卡死。"""

    finished = Signal(object)
    failed = Signal()

    def __init__(self, provider_cb):
        super().__init__()
        self._provider_cb = provider_cb

    def run(self) -> None:
        try:
            digest = self._provider_cb()
        except Exception:
            logger.error("后台构建波形摘要失败", exc_info=True)
            self.failed.emit()
            return
        self.finished.emit(digest)


class AIAssistPanel(QFrame):
    request_close = Signal()

    def __init__(self, service: AIService, parent=None):
        super().__init__(parent)
        self._service = service
        self._config_apply_cb = None
        self._script_apply_cb = None
        self._waveform_provider_cb = None
        self._digest_thread = None
        self._digest_worker = None
        self._pending_waveform_text = ""
        self.setObjectName("aiAssistPanel")
        self.setStyleSheet(_PANEL_STYLE)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        self._chat = ChatView()
        root.addWidget(self._chat, 1)

        bottom_bar = QFrame()
        bottom_bar.setObjectName("aiBottomBar")
        bottom_layout = QVBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        bottom_layout.setSpacing(12)

        self._quick_row = self._build_quick_row()
        bottom_layout.addWidget(self._quick_row)

        self._input = _InputEdit()
        self._input.setObjectName("aiInput")
        self._input.setPlaceholderText("输入问题，Enter 发送 / Shift+Enter 换行")
        self._input.submitted.connect(self._on_send_clicked)
        bottom_layout.addWidget(self._input)

        bottom_layout.addLayout(self._build_range_bar())
        bottom_layout.addLayout(self._build_action_bar())
        bottom_layout.addWidget(self._build_usage_bar())

        root.addWidget(bottom_bar)

        self._chat.add_system_message("AI 助手已就绪。")
        self._replay_history()
        self.refresh_quick_actions()
        self._wire_service()

    def _build_header(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("aiHeaderBar")
        bar.setFixedHeight(56)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(6)

        icon = QLabel()
        icon.setObjectName("aiPanelTitleIcon")
        icon.setFixedSize(18, 18)
        if os.path.isfile(_PANEL_ICON):
            icon.setPixmap(tinted_svg_pixmap(_PANEL_ICON, "#3b82f6", 18))
        layout.addWidget(icon)

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

        sep = QLabel("｜")
        sep.setObjectName("aiHeaderSep")
        layout.addWidget(sep)

        close_btn = QPushButton("×")
        close_btn.setObjectName("aiCloseBtn")
        close_btn.setFixedWidth(28)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setToolTip("关闭面板")
        close_btn.clicked.connect(self.request_close.emit)
        layout.addWidget(close_btn)
        return bar

    def _populate_models(self) -> None:
        settings = self._service.settings
        fixed = settings.model_mode == "fixed"
        target = settings.effective_model if fixed else ""
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.addItem("自动（按页面）", "")
        for model in self._service.available_models():
            self._model_combo.addItem(model, model)
        if fixed and target:
            idx = self._model_combo.findData(target)
            if idx < 0:
                self._model_combo.addItem(target, target)
                idx = self._model_combo.count() - 1
            self._model_combo.setCurrentIndex(idx)
        else:
            self._model_combo.setCurrentIndex(0)
        self._model_combo.blockSignals(False)
        self._service.set_model_override(target or None)

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
        if os.path.isfile(_SPARKLES_ICON):
            self._analyze_btn.setIcon(tinted_svg_icon(_SPARKLES_ICON, "#3b82f6", 13))
            self._analyze_btn.setIconSize(QSize(13, 13))
        self._analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self._analyze_btn)

        self._draft_btn = QPushButton("生成草案")
        self._draft_btn.setObjectName("aiScriptBtn")
        self._draft_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._draft_btn.setToolTip("根据输入框需求生成测试配置/脚本草案（预览校验后才应用）")
        if os.path.isfile(_SPARKLES_ICON):
            self._draft_btn.setIcon(tinted_svg_icon(_SPARKLES_ICON, "#818cf8", 13))
            self._draft_btn.setIconSize(QSize(13, 13))
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

        self._model_combo = QComboBox()
        self._model_combo.setObjectName("aiModelCombo")
        self._model_combo.setMinimumWidth(120)
        self._model_combo.setToolTip("手动切换模型（按 Profile 自动选择 / 指定模型）")
        self._populate_models()
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self._model_combo)

        self._send_btn = _PressScaleButton("发送")
        self._send_btn.setObjectName("aiSendBtn")
        self._send_btn.setCursor(QCursor(Qt.PointingHandCursor))
        if os.path.isfile(_SEND_ICON):
            self._send_btn.setIcon(tinted_svg_icon(_SEND_ICON, "#ffffff", 14))
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
        if self._digest_thread is not None:
            self._chat.add_system_message("正在构建波形摘要，请稍候。")
            return
        text = self._input.toPlainText().strip() or "请分析以下波形数据的特征、异常与可能原因。"
        self._input.clear()
        self._pending_waveform_text = text
        self._waveform_btn.setEnabled(False)
        self._chat.add_system_message("正在后台构建波形摘要…")

        self._digest_thread = QThread()
        self._digest_worker = _DigestWorker(self._waveform_provider_cb)
        self._digest_worker.moveToThread(self._digest_thread)
        self._digest_thread.started.connect(self._digest_worker.run)
        self._digest_worker.finished.connect(self._on_digest_ready)
        self._digest_worker.failed.connect(self._on_digest_failed)
        self._digest_worker.finished.connect(self._digest_thread.quit)
        self._digest_worker.failed.connect(self._digest_thread.quit)
        self._digest_thread.finished.connect(self._cleanup_digest_thread)
        self._digest_thread.start()

    def _on_digest_ready(self, digest) -> None:
        if digest is None or not getattr(digest, "stats", None):
            self._chat.add_system_message("当前没有可分析的波形数据。")
            return
        text = self._pending_waveform_text or "请分析以下波形数据的特征、异常与可能原因。"
        self._chat.add_user_message(f"[发送波形] {text}")
        self._service.send_with_waveform(text, digest)

    def _on_digest_failed(self) -> None:
        self._chat.add_system_message("获取波形数据失败，请查看日志。")

    def _cleanup_digest_thread(self) -> None:
        if self._digest_worker is not None:
            self._digest_worker.deleteLater()
            self._digest_worker = None
        if self._digest_thread is not None:
            self._digest_thread.deleteLater()
            self._digest_thread = None
        self._pending_waveform_text = ""
        self._waveform_btn.setEnabled(True)

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

    def confirm_action(self, spec, arguments: dict, reason: str = "") -> "ConfirmResult":
        """供 ActionDispatcher 注入的确认回调：在聊天内嵌入确认卡片。

        指令 / shell 类需确认动作（high/critical）走此回调，故卡片仅在
        真正需要确认时出现；其余动作不会插入卡片。回调对 dispatcher 保持
        同步语义：用局部 QEventLoop 阻塞直到用户在卡片上做出选择。

        返回 ConfirmResult：
          - 运行        -> confirmed=True；
          - 添加到白名单 -> confirmed=True + remember_resident=True（仅 high）；
          - 拒绝        -> confirmed=False。
        """
        from core.ai.actions.dispatcher import ConfirmResult

        description = spec.description or ""
        if reason:
            description = f"{description}\n{reason}".strip()

        card = self._chat.add_action_confirm(
            action_name=spec.name,
            description=description,
            risk_level=spec.risk_level,
            arguments=arguments,
        )

        loop = QEventLoop(self)
        result = ConfirmResult(confirmed=False)

        def _finish(outcome: ConfirmResult, status_text: str) -> None:
            result.confirmed = outcome.confirmed
            result.remember_session = outcome.remember_session
            result.remember_resident = outcome.remember_resident
            card.finalize(status_text)
            if loop.isRunning():
                loop.quit()

        card.run_clicked.connect(
            lambda: _finish(ConfirmResult(confirmed=True), "✓ 已选择运行")
        )
        card.reject_clicked.connect(
            lambda: _finish(ConfirmResult(confirmed=False), "⛔ 已拒绝执行")
        )
        card.allow_clicked.connect(
            lambda: _finish(
                ConfirmResult(confirmed=True, remember_resident=True),
                "✓ 已添加到白名单并运行",
            )
        )

        loop.exec()
        return result

    def _on_action_result(self, outcome) -> None:
        if outcome is None:
            return
        status = getattr(outcome, "status", "")
        name = getattr(outcome, "name", "")
        message = getattr(outcome, "message", "")
        auto_approved = getattr(outcome, "auto_approved", False)
        if status == "executed" and auto_approved:
            prefix = "⚡ 已按白名单自动执行"
        else:
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
