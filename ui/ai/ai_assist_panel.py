"""AIAssistPanel：右侧 AI 助手面板。

组成：标题栏 + ChatView + 输入框 + 发送/分析日志按钮。
通过 AIService 信号驱动 UI，自身不做阻塞 IO。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QEasingCurve,
    QEventLoop,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QThread,
    Signal,
)
from PySide6.QtGui import QCursor, QKeyEvent
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from core.ai.ai_service import AIService
from core.ai.context_builder import ContextOptions
from core.ai.profiles import (
    fill_quick_action,
    get_quick_actions,
    quick_action_placeholders,
)
from core.ai.response_parser import ParsedResponse
from core.ai.schemas import CONFIG_DRAFT, SCRIPT_DRAFT
from ui.ai.chat_view import ChatView
from ui.resource_path import get_resource_base
from ui.utils.icon_utils import tinted_svg_icon, tinted_svg_pixmap
from log_config import get_logger

if TYPE_CHECKING:
    from core.ai.actions.dispatcher import ConfirmResult

logger = get_logger(__name__)

_NO_WAVEFORM_GUARD = (
    "[波形数据] 当前没有任何可分析的波形数据（内存中无波形，或所选范围内无数据点）。\n"
    "严格要求：你绝对不能编造、估算或假设任何波形读数（如电流峰值、周期、尖峰个数、"
    "幅值、时间等）。请明确告知用户「当前没有可分析的波形数据」，并提示用户先采集或导入"
    "（Import）波形后再分析。仅可就用户的纯文字问题作答，不得输出任何虚构的测量数值或分析结论。"
)

_AI_SVG_DIR = os.path.join(get_resource_base(), "resources", "icons_svg", "ai")
_SEND_ICON = os.path.join(_AI_SVG_DIR, "send.svg")
_PANEL_ICON = os.path.join(_AI_SVG_DIR, "ai_panel.svg")
_SPARKLES_ICON = os.path.join(_AI_SVG_DIR, "sparkles.svg")
_INSPECT_ICON = os.path.join(_AI_SVG_DIR, "inspect.svg")
_CLEAR_ICON = os.path.join(_AI_SVG_DIR, "clear.svg")
_SETTINGS_ICON = os.path.join(_AI_SVG_DIR, "settings.svg")
_EXPORT_ICON = os.path.join(_AI_SVG_DIR, "export.svg")
_CLOSE_ICON = os.path.join(_AI_SVG_DIR, "close.svg")

_PANEL_STYLE = """
QFrame#aiAssistPanel {
    background-color: #070709;
    border-left: 1px solid #1e293b;
    border-radius: 0px;
}
QFrame#aiHeaderBar {
    background-color: #020617;
    border: none;
    border-bottom: 1px solid #1e293b;
    border-radius: 0px;
}
QFrame#aiBottomBar {
    background-color: #030616;
    border-top: 1px solid #1e293b;
}
QFrame#aiComposeBox {
    background-color: #070709;
    border: 1px solid #1e293b;
    border-radius: 12px;
}
QFrame#aiComposeBox[focused="true"] {
    border: 1px solid #3b82f6;
}
QFrame#aiInputArea {
    background-color: #070709;
    border: none;
    border-top-left-radius: 11px;
    border-top-right-radius: 11px;
}
QFrame#aiControlsArea {
    background-color: #04060f;
    border: none;
    border-top: 1px solid #1e293b;
    border-bottom-left-radius: 11px;
    border-bottom-right-radius: 11px;
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
QPushButton#aiIconBtn {
    min-width: 28px;
    min-height: 28px;
    max-width: 28px;
    max-height: 28px;
    padding: 0px;
    border: none;
    border-radius: 6px;
    background-color: transparent;
}
QPushButton#aiIconBtn:hover {
    background-color: #1e293b;
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
    background-color: transparent;
    color: #e2e8f0;
    border: none;
    border-radius: 0px;
    padding: 2px 2px;
    font-size: 12px;
}
QPlainTextEdit#aiInput:focus {
    border: none;
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
QPushButton#aiExportBtn {
    min-height: 22px;
    padding: 4px 12px;
    border: 1px solid #2a3344;
    border-radius: 8px;
    background-color: #131a26;
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#aiExportBtn:hover {
    background-color: #1b2433;
    color: #cbd5e1;
}
QLabel#aiRangeLabel {
    color: #64748b;
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.4px;
    background: transparent;
    border: none;
}
QComboBox#aiLevelCombo {
    min-height: 22px;
    padding: 1px 6px;
    border: 1px solid #1e293b;
    border-radius: 4px;
    background-color: #04060f;
    color: #cbd5e1;
    font-size: 10px;
    font-weight: 700;
}
QComboBox#aiLevelCombo QAbstractItemView {
    background-color: #04060f;
    color: #cbd5e1;
    selection-background-color: #1d3a6e;
}
QSpinBox#aiLinesSpin {
    min-height: 22px;
    padding: 1px 4px;
    border: 1px solid #1e293b;
    border-radius: 4px;
    background-color: #04060f;
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


class _FlowLayout(QLayout):
    """自动换行的流式布局：宽度不足时把控件折到下一行，避免横向撑宽面板。"""

    def __init__(self, parent=None, margin: int = 0, spacing: int = 6):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items: list = []

    def __del__(self):
        while self._items:
            self._items.pop()

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(
            margins.left() + margins.right(),
            margins.top() + margins.bottom(),
        )
        return size

    def _do_layout(self, rect, test_only):
        margins = self.contentsMargins()
        effective = rect.adjusted(
            margins.left(), margins.top(), -margins.right(), -margins.bottom()
        )
        spacing = self.spacing()
        x = effective.x()
        y = effective.y()
        line_height = 0
        line_items: list = []

        def place_line():
            if test_only:
                return
            for line_item, line_x, item_size in line_items:
                offset_y = y + (line_height - item_size.height()) // 2
                line_item.setGeometry(QRect(QPoint(line_x, offset_y), item_size))

        for item in self._items:
            item_size = item.sizeHint()
            next_x = x + item_size.width() + spacing
            if next_x - spacing > effective.right() and line_height > 0:
                place_line()
                line_items = []
                x = effective.x()
                y = y + line_height + spacing
                next_x = x + item_size.width() + spacing
                line_height = 0
            line_items.append((item, x, item_size))
            x = next_x
            line_height = max(line_height, item_size.height())
        place_line()
        return y + line_height - rect.y() + margins.bottom()


class _InputEdit(QPlainTextEdit):
    """Enter 发送，Shift+Enter 换行；聚焦时显示蓝色焦点环，高度随内容弹性自适应。"""

    submitted = Signal()

    _MIN_HEIGHT = 80
    _MAX_HEIGHT = 160

    focus_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFixedHeight(self._MIN_HEIGHT)

        self.document().documentLayout().documentSizeChanged.connect(
            self._adjust_height
        )

    def _adjust_height(self) -> None:
        doc_height = int(self.document().size().height())
        target = max(self._MIN_HEIGHT, min(self._MAX_HEIGHT, doc_height + 18))
        if target != self.height():
            self.setFixedHeight(target)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self.focus_changed.emit(True)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.focus_changed.emit(False)

    def inputMethodEvent(self, event) -> None:
        super().inputMethodEvent(event)
        self.viewport().update()

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

    def __init__(self, provider_cb, x_range=None, marker=None):
        super().__init__()
        self._provider_cb = provider_cb
        self._x_range = x_range
        self._marker = marker

    def run(self) -> None:
        try:
            digest = self._provider_cb(self._x_range, self._marker)
        except Exception:
            logger.error("后台构建波形摘要失败", exc_info=True)
            self.failed.emit()
            return
        self.finished.emit(digest)


class AIAssistPanel(QFrame):
    request_close = Signal()
    request_open = Signal()
    pick_requested = Signal()

    def __init__(self, service: AIService, parent=None):
        super().__init__(parent)
        self._service = service
        self._config_apply_cb = None
        self._script_apply_cb = None
        self._waveform_provider_cb = None
        self._waveform_range_getter = None
        self._waveform_marker_getter = None
        self._digest_thread = None
        self._digest_worker = None
        self._pending_waveform_text = ""
        self._pending_waveform_via_button = False
        self._pending_picked_context = ""
        self._transcript: list[dict] = []
        self._last_user_text = ""
        self._last_assistant_text = ""
        self._session_started_at = datetime.now()
        self.setObjectName("aiAssistPanel")
        self.setStyleSheet(_PANEL_STYLE)
        self.setMinimumWidth(240)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())

        self._chat = ChatView()
        self._chat.feedback_submitted.connect(self._on_feedback)
        self._chat.curate_requested.connect(self._on_curate_requested)
        root.addWidget(self._chat, 1)

        bottom_bar = QFrame()
        bottom_bar.setObjectName("aiBottomBar")
        bottom_layout = QVBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        bottom_layout.setSpacing(12)

        self._quick_row = self._build_quick_row()
        bottom_layout.addWidget(self._quick_row)

        compose_box = QFrame()
        compose_box.setObjectName("aiComposeBox")
        compose_layout = QVBoxLayout(compose_box)
        compose_layout.setContentsMargins(0, 0, 0, 0)
        compose_layout.setSpacing(0)

        input_area = QFrame()
        input_area.setObjectName("aiInputArea")
        input_layout = QVBoxLayout(input_area)
        input_layout.setContentsMargins(12, 12, 12, 12)
        input_layout.setSpacing(0)

        self._input = _InputEdit()
        self._input.setObjectName("aiInput")
        self._input.setPlaceholderText("Ask a question, Enter to send / Shift+Enter for new line")
        self._input.submitted.connect(self._on_send_clicked)
        self._compose_box = compose_box
        self._input.focus_changed.connect(self._on_input_focus_changed)
        input_layout.addWidget(self._input)
        compose_layout.addWidget(input_area)

        controls_area = QFrame()
        controls_area.setObjectName("aiControlsArea")
        controls_layout = QVBoxLayout(controls_area)
        controls_layout.setContentsMargins(12, 10, 12, 12)
        controls_layout.setSpacing(10)
        controls_layout.addLayout(self._build_range_bar())
        controls_layout.addLayout(self._build_action_bar())
        controls_layout.addLayout(self._build_send_bar())
        compose_layout.addWidget(controls_area)

        bottom_layout.addWidget(compose_box)

        bottom_layout.addWidget(self._build_usage_bar())

        root.addWidget(bottom_bar)

        self._chat.add_system_message("AI Assistant is ready.")
        self._replay_history()
        self.refresh_quick_actions()
        self._wire_service()
        self._service.start_telemetry()

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

        title = QLabel("AI Assistant")
        title.setObjectName("aiPanelTitle")
        title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        layout.addWidget(title)
        layout.addStretch(1)

        self._clear_btn = QPushButton()
        self._clear_btn.setObjectName("aiIconBtn")
        self._clear_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._clear_btn.setToolTip("Clear current conversation history")
        if os.path.isfile(_CLEAR_ICON):
            self._clear_btn.setIcon(tinted_svg_icon(_CLEAR_ICON, "#94a3b8", 16))
            self._clear_btn.setIconSize(QSize(16, 16))
        self._clear_btn.clicked.connect(self._on_clear_clicked)
        layout.addWidget(self._clear_btn)

        self._export_btn = QPushButton()
        self._export_btn.setObjectName("aiIconBtn")
        self._export_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._export_btn.setToolTip(
            "Export this session's debug info: questions / system prompts / AI replies / executed actions / audit / usage (Markdown)"
        )
        if os.path.isfile(_EXPORT_ICON):
            self._export_btn.setIcon(tinted_svg_icon(_EXPORT_ICON, "#94a3b8", 16))
            self._export_btn.setIconSize(QSize(16, 16))
        self._export_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(self._export_btn)

        self._settings_btn = QPushButton()
        self._settings_btn.setObjectName("aiIconBtn")
        self._settings_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._settings_btn.setToolTip("Settings")
        if os.path.isfile(_SETTINGS_ICON):
            self._settings_btn.setIcon(tinted_svg_icon(_SETTINGS_ICON, "#94a3b8", 16))
            self._settings_btn.setIconSize(QSize(16, 16))
        self._settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(self._settings_btn)

        sep = QLabel("｜")
        sep.setObjectName("aiHeaderSep")
        layout.addWidget(sep)

        close_btn = QPushButton()
        close_btn.setObjectName("aiCloseBtn")
        close_btn.setFixedWidth(28)
        close_btn.setCursor(QCursor(Qt.PointingHandCursor))
        close_btn.setToolTip("Close panel")
        if os.path.isfile(_CLOSE_ICON):
            close_btn.setIcon(tinted_svg_icon(_CLOSE_ICON, "#64748b", 16))
            close_btn.setIconSize(QSize(16, 16))
        close_btn.clicked.connect(self.request_close.emit)
        layout.addWidget(close_btn)
        return bar

    def _on_input_focus_changed(self, focused: bool) -> None:
        box = getattr(self, "_compose_box", None)
        if box is None:
            return
        box.setProperty("focused", "true" if focused else "false")
        box.style().unpolish(box)
        box.style().polish(box)

    def _populate_models(self) -> None:
        settings = self._service.settings
        fixed = settings.model_mode == "fixed"
        target = settings.effective_model if fixed else ""
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        self._model_combo.addItem("Auto (Page)", "")
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
            self._chat.add_system_message(f"Model switched: {model}")
        else:
            self._chat.add_system_message("Model reset to: Auto (Page)")

    def _build_quick_row(self) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        layout = _FlowLayout(row, margin=0, spacing=6)
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
        self._quick_row.setVisible(bool(actions))

    def _on_quick_clicked(self, text: str) -> None:
        placeholders = quick_action_placeholders(text)
        if placeholders:
            values = self._prompt_quick_action_values(text, placeholders)
            if values is None:
                return
            text = fill_quick_action(text, values)
        self._input.setPlainText(text)
        self._on_send_clicked()

    def _prompt_quick_action_values(
        self, template: str, placeholders: list[str]
    ) -> dict[str, str] | None:
        """对带占位符的快捷指令弹轻量输入框；取消返回 None。"""
        from PySide6.QtWidgets import QDialogButtonBox, QFormLayout, QLineEdit

        dialog = QDialog(parent=self)
        dialog.setWindowTitle("Fill Quick Action Parameters")
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        tip = QLabel(template)
        tip.setWordWrap(True)
        layout.addWidget(tip)

        form = QFormLayout()
        form.setSpacing(8)
        edits: dict[str, QLineEdit] = {}
        for name in placeholders:
            edit = QLineEdit()
            edit.setPlaceholderText(f"Enter {name}")
            form.addRow(name, edit)
            edits[name] = edit
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog
        )
        ok_btn = buttons.button(QDialogButtonBox.Ok)
        ok_btn.setAutoDefault(True)
        ok_btn.setDefault(True)
        cancel_btn = buttons.button(QDialogButtonBox.Cancel)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if placeholders:
            edits[placeholders[0]].setFocus()

        if dialog.exec() != QDialog.Accepted:
            return None
        return {name: edit.text().strip() for name, edit in edits.items()}

    def _build_range_bar(self) -> QLayout:
        layout = _FlowLayout(spacing=6)
        layout.setContentsMargins(0, 0, 0, 0)

        level_label = QLabel("Log Level")
        level_label.setObjectName("aiRangeLabel")
        layout.addWidget(level_label)

        self._level_combo = QComboBox()
        self._level_combo.setObjectName("aiLevelCombo")
        self._level_combo.addItems(_LOG_LEVELS)
        self._level_combo.setCurrentText("INFO")
        self._level_combo.setToolTip("Only keep logs at or above this level during analysis")
        layout.addWidget(self._level_combo)

        lines_label = QLabel("Max Lines")
        lines_label.setObjectName("aiRangeLabel")
        layout.addWidget(lines_label)

        self._lines_spin = QSpinBox()
        self._lines_spin.setObjectName("aiLinesSpin")
        self._lines_spin.setRange(20, _MAX_LINES_CAP)
        self._lines_spin.setSingleStep(50)
        self._lines_spin.setValue(300)
        self._lines_spin.setToolTip(f"Max lines taken per log type (cap {_MAX_LINES_CAP})")
        layout.addWidget(self._lines_spin)

        return layout

    def _build_action_bar(self) -> QLayout:
        layout = _FlowLayout(spacing=8)
        layout.setContentsMargins(0, 0, 0, 0)

        self._select_btn = QPushButton("Select")
        self._select_btn.setObjectName("aiAnalyzeBtn")
        self._select_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._select_btn.setToolTip(
            "Pick any element/data on the page (Ctrl+Shift+C) and attach it to the next message"
        )
        if os.path.isfile(_INSPECT_ICON):
            self._select_btn.setIcon(tinted_svg_icon(_INSPECT_ICON, "#34d399", 13))
            self._select_btn.setIconSize(QSize(13, 13))
        self._select_btn.clicked.connect(self.pick_requested.emit)
        layout.addWidget(self._select_btn)

        self._analyze_btn = QPushButton("Analyze")
        self._analyze_btn.setObjectName("aiAnalyzeBtn")
        self._analyze_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._analyze_btn.setToolTip("Analyze based on recent run logs")
        if os.path.isfile(_SPARKLES_ICON):
            self._analyze_btn.setIcon(tinted_svg_icon(_SPARKLES_ICON, "#3b82f6", 13))
            self._analyze_btn.setIconSize(QSize(13, 13))
        self._analyze_btn.clicked.connect(self._on_analyze_clicked)
        layout.addWidget(self._analyze_btn)

        self._draft_btn = QPushButton("Script")
        self._draft_btn.setObjectName("aiScriptBtn")
        self._draft_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._draft_btn.setToolTip("Generate a test config/script draft from the input (applied only after preview validation)")
        if os.path.isfile(_SPARKLES_ICON):
            self._draft_btn.setIcon(tinted_svg_icon(_SPARKLES_ICON, "#818cf8", 13))
            self._draft_btn.setIconSize(QSize(13, 13))
        self._draft_btn.clicked.connect(self._on_draft_clicked)
        layout.addWidget(self._draft_btn)

        self._waveform_btn = QPushButton("Send Waveform to AI")
        self._waveform_btn.setObjectName("aiAnalyzeBtn")
        self._waveform_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._waveform_btn.setToolTip("Send the current page's waveform (summary + downsampled) to AI for analysis")
        self._waveform_btn.clicked.connect(self._on_waveform_clicked)
        self._waveform_btn.setVisible(False)
        layout.addWidget(self._waveform_btn)
        return layout

    def _build_send_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._model_combo = QComboBox()
        self._model_combo.setObjectName("aiModelCombo")
        self._model_combo.setMinimumWidth(80)
        self._model_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._model_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self._model_combo.setMinimumContentsLength(6)
        self._model_combo.setToolTip("Manually switch model (auto by Profile / specify a model)")
        self._populate_models()
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        layout.addWidget(self._model_combo, 1)

        self._send_btn = _PressScaleButton("Send")
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
        self._usage_label = QLabel("Usage (tokens): None")
        self._usage_label.setObjectName("aiUsageLabel")
        self._usage_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._usage_label)
        layout.addStretch(1)
        return row

    def set_waveform_provider_callback(self, callback) -> None:
        """注入波形提供回调：callback(x_range, marker) -> WaveformDigest | None。

        x_range/marker 由 UI 线程的 getter 在进后台线程前取好快照传入；
        传入 None 表示当前页面无波形源，隐藏"发送波形给 AI"按钮。
        """
        self._waveform_provider_cb = callback
        if hasattr(self, "_waveform_btn"):
            self._waveform_btn.setVisible(callback is not None)

    def set_waveform_range_getter(self, getter) -> None:
        """注入可见 X 范围 getter：getter() -> (x0, x1) | None（UI 线程同步调用）。"""
        self._waveform_range_getter = getter

    def set_waveform_marker_getter(self, getter) -> None:
        """注入 Marker getter：getter() -> {"a","b"} | None（UI 线程同步调用）。"""
        self._waveform_marker_getter = getter

    def _on_waveform_clicked(self) -> None:
        if self._waveform_provider_cb is None:
            self._chat.add_system_message("No waveform data available to send on the current page.")
            return
        text = self._input.toPlainText().strip() or "Please analyze the characteristics, anomalies and possible causes of the following waveform data."
        self._input.clear()
        self._start_digest_send(text, via_button=True)

    def _start_digest_send(self, text: str, *, via_button: bool) -> None:
        """统一的波形分析发送入口：后台构建摘要后注入上下文再发送。

        via_button=True 走"发送波形"按钮（用户气泡加 [发送波形] 前缀）；
        via_button=False 走普通文字提问（datalog 页自动带摘要，用户气泡显示原文）。
        """
        if self._digest_thread is not None:
            self._chat.add_system_message("Building waveform summary, please wait.")
            return
        self._pending_waveform_text = text
        self._pending_waveform_via_button = via_button
        self._waveform_btn.setEnabled(False)
        self._chat.add_system_message("Building waveform summary in the background…")

        x_range = None
        marker = None
        if self._waveform_range_getter is not None:
            try:
                x_range = self._waveform_range_getter()
            except Exception:
                logger.error("读取可见 X 范围失败", exc_info=True)
        if self._waveform_marker_getter is not None:
            try:
                marker = self._waveform_marker_getter()
            except Exception:
                logger.error("读取 Marker 范围失败", exc_info=True)

        self._digest_thread = QThread()
        self._digest_worker = _DigestWorker(
            self._waveform_provider_cb, x_range=x_range, marker=marker
        )
        self._digest_worker.moveToThread(self._digest_thread)
        self._digest_thread.started.connect(self._digest_worker.run)
        self._digest_worker.finished.connect(self._on_digest_ready)
        self._digest_worker.failed.connect(self._on_digest_failed)
        self._digest_worker.finished.connect(self._digest_thread.quit)
        self._digest_worker.failed.connect(self._digest_thread.quit)
        self._digest_thread.finished.connect(self._cleanup_digest_thread)
        self._digest_thread.start()

    def _on_digest_ready(self, digest) -> None:
        text = self._pending_waveform_text or "Please analyze the characteristics, anomalies and possible causes of the following waveform data."
        via_button = self._pending_waveform_via_button
        if digest is None or not getattr(digest, "stats", None):
            if via_button:
                self._chat.add_system_message("No waveform data available to analyze.")
                return
            self._chat.add_system_message(
                "No waveform data available to analyze; the assistant will be told not "
                "to fabricate any waveform readings."
            )
            self._record("user", text=text)
            self._last_user_text = text
            self._chat.add_user_message(text)
            picked = self._take_picked_context()
            self._record_injected_context(
                picked=picked, waveform_guard=_NO_WAVEFORM_GUARD
            )
            self._service.send(
                text,
                extra_context=picked,
                waveform_context=_NO_WAVEFORM_GUARD,
            )
            return
        scope = self._format_waveform_scope(digest)
        if scope:
            self._chat.add_system_message(scope)
        picked = self._take_picked_context()
        if via_button:
            self._record("user", text=f"[Send Waveform] {text}")
            self._chat.add_user_message(f"[Send Waveform] {text}")
        else:
            self._record("user", text=text)
            self._chat.add_user_message(text)
        self._record_injected_context(digest=digest, picked=picked, scope=scope)
        self._last_user_text = text
        self._service.send_with_waveform(text, digest, extra_context=picked)

    @staticmethod
    def _format_waveform_scope(digest) -> str:
        """生成本轮波形分析范围的提示文本，让用户确认 AI 用的是最新 Marker/可见范围。"""
        def _fmt(value) -> str:
            try:
                return f"{float(value):.6g}"
            except (TypeError, ValueError):
                return str(value)

        parts: list[str] = []
        window = getattr(digest, "window", None)
        if window:
            if window.get("full"):
                parts.append("可见范围：全程")
            else:
                parts.append(
                    f"可见范围：{_fmt(window.get('x0'))}~{_fmt(window.get('x1'))} s"
                )
        marker = getattr(digest, "marker_segment", None)
        if marker and marker.get("per_channel"):
            parts.append(
                f"Marker A={_fmt(marker.get('a'))} s, "
                f"B={_fmt(marker.get('b'))} s, "
                f"时长={_fmt(marker.get('duration_s'))} s"
            )
        stats = getattr(digest, "stats", None) or []
        raw_points = sum(int(getattr(s, "point_count", 0) or 0) for s in stats)
        downsampled = getattr(digest, "downsampled", None) or {}
        ds_points = sum(
            len((v or {}).get("values", []) or []) for v in downsampled.values()
        )
        if raw_points or ds_points:
            parts.append(
                f"点数：采样前 {raw_points} → 采样后 {ds_points}"
                f"（{len(stats)} 通道）"
            )
        if not parts:
            return ""
        return "本轮分析范围 — " + "；".join(parts)

    def _on_digest_failed(self) -> None:
        text = self._pending_waveform_text
        via_button = self._pending_waveform_via_button
        if via_button or not text:
            self._chat.add_system_message("Failed to fetch waveform data, please check the logs.")
            return
        self._chat.add_system_message(
            "Failed to fetch waveform data; the assistant will be told not to "
            "fabricate any waveform readings."
        )
        self._record("user", text=text)
        self._last_user_text = text
        self._chat.add_user_message(text)
        self._record_injected_context(waveform_guard=_NO_WAVEFORM_GUARD)
        self._service.send(text, waveform_context=_NO_WAVEFORM_GUARD)

    def _cleanup_digest_thread(self) -> None:
        if self._digest_worker is not None:
            self._digest_worker.deleteLater()
            self._digest_worker = None
        if self._digest_thread is not None:
            self._digest_thread.deleteLater()
            self._digest_thread = None
        self._pending_waveform_text = ""
        self._pending_waveform_via_button = False
        self._waveform_btn.setEnabled(True)

    def _on_usage_updated(self, turn, session) -> None:
        if turn is None:
            self._usage_label.setText("Usage (tokens): None")
            return
        try:
            tps = turn.output_tps
            sess_prompt = getattr(session, "prompt_tokens_total", 0)
            sess_completion = getattr(session, "completion_tokens_total", 0)
            requests = getattr(session, "requests", 0)
            self._record(
                "usage",
                turn_prompt=getattr(turn, "prompt_tokens", 0),
                turn_completion=getattr(turn, "completion_tokens", 0),
                output_tps=round(float(tps), 2),
                session_prompt=sess_prompt,
                session_completion=sess_completion,
                requests=requests,
            )
            self._usage_label.setText(
                f"This turn ↑{turn.prompt_tokens} ↓{turn.completion_tokens} tokens @ "
                f"{tps:.1f} tok·s⁻¹ | Session ↑{sess_prompt} ↓{sess_completion} tokens"
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
        self._service.action_requested.connect(self._on_action_requested)
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
        self._chat.add_system_message("(Restored previous conversation history)")

    def _on_clear_clicked(self) -> None:
        self._service.clear_history()
        self._transcript.clear()
        self._session_started_at = datetime.now()
        self._chat.add_system_message("Conversation history cleared.")

    def _on_stream_started(self) -> None:
        self._chat.begin_stream_message()

    def _on_stream_delta(self, chunk: str) -> None:
        self._chat.append_stream_delta(chunk)

    def _on_stream_finished(self, content: str) -> None:
        self._record("assistant", text=content or "")
        self._last_assistant_text = content or ""
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

        self._record(
            "confirm_prompt",
            name=spec.name,
            risk_level=spec.risk_level,
            arguments=arguments,
            reason=reason,
        )

        card = self._chat.add_action_confirm(
            action_name=spec.name,
            description=description,
            risk_level=spec.risk_level,
            arguments=arguments,
        )

        loop = QEventLoop(self)
        result = ConfirmResult(confirmed=False)

        def _finish(outcome: ConfirmResult, status_text: str) -> None:
            self._record(
                "confirm_decision",
                name=spec.name,
                confirmed=outcome.confirmed,
                remember_session=outcome.remember_session,
                remember_resident=outcome.remember_resident,
                status_text=status_text,
            )
            result.confirmed = outcome.confirmed
            result.remember_session = outcome.remember_session
            result.remember_resident = outcome.remember_resident
            card.finalize(status_text)
            if loop.isRunning():
                loop.quit()

        card.run_clicked.connect(
            lambda: _finish(ConfirmResult(confirmed=True), "✓ Run selected")
        )
        card.reject_clicked.connect(
            lambda: _finish(ConfirmResult(confirmed=False), "⛔ Execution rejected")
        )
        card.allow_clicked.connect(
            lambda: _finish(
                ConfirmResult(confirmed=True, remember_resident=True),
                "✓ Added to whitelist and run",
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
        self._record(
            "action_result",
            name=name,
            status=status,
            auto_approved=bool(auto_approved),
            risk_level=getattr(outcome, "risk_level", ""),
            message=message,
            result=getattr(outcome, "result", {}),
        )
        if status == "executed" and auto_approved:
            prefix = "⚡ Auto-executed via whitelist"
        else:
            prefix = {
                "executed": "✓ Executed",
                "denied": "⛔ Denied",
                "cancelled": "✗ Cancelled",
                "failed": "⚠ Execution failed",
            }.get(status, status)
        text = f"{prefix} action [{name}]"
        if message:
            text += f": {message}"
        self._chat.add_system_message(text)

    def attach_picked_context(self, label: str, content: str) -> None:
        """元素拾取器注入：把页面拾取到的内容挂为下一次发送的附带上下文。

        多次拾取累加；面板自动展开并提示用户已附加。下一次 send 时随
        extra_context 一并发出并清空。
        """
        content = (content or "").strip()
        if not content:
            return
        block = f"[页面拾取内容：{label}]\n{content}"
        if self._pending_picked_context:
            self._pending_picked_context += "\n\n" + block
        else:
            self._pending_picked_context = block
        self.request_open.emit()
        self._input.setFocus()
        self._chat.add_system_message(
            f"已附加页面内容「{label}」，将随下一条消息发送给 AI。"
        )

    def _take_picked_context(self) -> str:
        ctx = self._pending_picked_context
        self._pending_picked_context = ""
        return ctx

    def set_config_apply_callback(self, callback) -> None:
        """注入测试配置草案 apply 回调：callback(ConfigDraft) -> (ok, message)。"""
        self._config_apply_cb = callback

    def set_script_apply_callback(self, callback) -> None:
        """注入测试脚本草案 apply 回调：callback(nodes) -> (ok, message)。"""
        self._script_apply_cb = callback

    def _record(self, kind: str, **fields) -> None:
        """记录一条会话流水，用于导出调试信息。"""
        entry = {"ts": datetime.now().isoformat(timespec="seconds"), "kind": kind}
        entry.update(fields)
        self._transcript.append(entry)

    def _record_injected_context(
        self,
        *,
        digest=None,
        picked: str = "",
        scope: str = "",
        waveform_guard: str = "",
    ) -> None:
        """记录本轮随用户提问一起喂给模型的注入上下文（数据是如何传递的）。

        让导出流水能看清「解读 Datalog」这类问题里，波形摘要 / 拾取内容 /
        无波形守卫等数据块是如何随消息传给 AI 的，而不只是看到用户的一句话。
        """
        blocks: list[dict] = []
        if digest is not None:
            try:
                from core.ai.prompt_manager import format_waveform_digest

                waveform_text = format_waveform_digest(digest)
            except Exception:
                logger.error("格式化波形摘要用于流水记录失败", exc_info=True)
                waveform_text = ""
            if waveform_text:
                blocks.append({"source": "波形数据摘要", "text": waveform_text})
        if waveform_guard:
            blocks.append({"source": "无波形守卫", "text": waveform_guard})
        if picked:
            blocks.append({"source": "页面拾取内容", "text": picked})
        if not blocks:
            return
        self._record("context", scope=scope or "", blocks=blocks)

    def _on_action_requested(self, payload) -> None:
        if not isinstance(payload, dict):
            return
        self._record(
            "action_requested",
            name=payload.get("name", ""),
            arguments=payload.get("arguments", {}),
        )

    def _on_export_clicked(self) -> None:
        default_name = (
            "ai_session_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".md"
        )
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Session (Debug Info)",
            default_name,
            "Markdown (*.md)",
        )
        if not path:
            return
        try:
            content = self._build_export_markdown()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            logger.error("导出会话失败: %s", path, exc_info=True)
            self._chat.add_system_message("Failed to export session, please check the logs.")
            return
        self._chat.add_system_message(f"Session debug info exported: {path}")

    def _build_export_markdown(self) -> str:
        from core.ai.profiles import get_global_system_prompt, get_profile

        page_key = self._service.current_page_key()
        profile = get_profile(page_key)
        settings = self._service.settings
        lines: list[str] = []

        lines.append("# KK_Lab AI 会话调试导出")
        lines.append("")
        lines.append(
            f"- 导出时间：{datetime.now().isoformat(timespec='seconds')}"
        )
        lines.append(
            f"- 会话开始：{self._session_started_at.isoformat(timespec='seconds')}"
        )
        lines.append(f"- 当前页面 (page_key)：`{page_key or '_default'}`")
        lines.append(
            f"- 模型：`{getattr(settings, 'default_model', '')}` "
            f"（model_mode=`{getattr(settings, 'model_mode', '')}`，"
            f"stream=`{getattr(settings, 'stream', '')}`）"
        )
        lines.append(f"- 手动选择模型：`{self._model_combo.currentData() or '自动'}`")
        lines.append("")

        lines.append("## 系统提示（System Prompt）")
        lines.append("")
        lines.append("### 全局")
        lines.append("")
        lines.append("```text")
        lines.append(get_global_system_prompt())
        lines.append("```")
        lines.append("")
        lines.append("### 页面 Profile")
        lines.append("")
        lines.append("```text")
        lines.append(str(profile.get("system_prompt", "")))
        lines.append("```")
        lines.append("")

        lines.append("## 会话流水（按轮次分组的完整顺序流程）")
        lines.append("")
        lines.append(
            "> 每一轮从用户提问开始，依序记录：注入上下文（喂给模型的数据）→ "
            "请求执行指令 → 指令执行结果 → 确认卡片 → AI 回复 → 用量。"
        )
        lines.append("")
        if not self._transcript:
            lines.append("_（本轮会话暂无流水记录）_")
            lines.append("")
        else:
            lines.extend(self._format_rounds(self._transcript))

        lines.append("## 持久化历史（service.persisted_history）")
        lines.append("")
        history = self._service.persisted_history()
        if not history:
            lines.append("_（无）_")
        else:
            for item in history:
                role = item.get("role", "")
                lines.append(f"- **{role}**：{item.get('content', '')}")
        lines.append("")

        lines.append("## 动作审计日志（audit.log）")
        lines.append("")
        lines.append(self._read_audit_tail())
        lines.append("")

        return "\n".join(lines)

    def _format_rounds(self, transcript: list[dict]) -> list[str]:
        """把扁平流水按「轮次」分组并加步骤编号，让单轮调用顺序一目了然。

        每遇到一个 user / analysis 条目即开启新一轮；轮内每个条目依序编号
        （step 1、step 2 …），AI 回复 / 用量等都归入当轮，从而能看清一次
        提问到最终回答之间，数据注入、工具调用、确认、回复的完整顺序。
        """
        out: list[str] = []
        round_no = 0
        step_no = 0
        opened = False

        def _close_round() -> None:
            if opened:
                out.append("---")
                out.append("")

        for entry in transcript:
            kind = entry.get("kind", "")
            if kind in ("user", "analysis") or not opened:
                _close_round()
                round_no += 1
                step_no = 0
                opened = True
                ts = entry.get("ts", "")
                out.append(f"## 🔁 第 {round_no} 轮  `{ts}`")
                out.append("")
            step_no += 1
            out.extend(self._format_entry(entry, step=step_no))
        _close_round()
        return out

    def _format_entry(self, entry: dict, step: int | None = None) -> list[str]:
        ts = entry.get("ts", "")
        kind = entry.get("kind", "")
        out: list[str] = []
        if kind == "user":
            out.append(f"### 🧑 用户  `{ts}`")
            out.append("")
            out.append(str(entry.get("text", "")))
        elif kind == "assistant":
            out.append(f"### 🤖 AI 回复  `{ts}`")
            out.append("")
            out.append(str(entry.get("text", "")))
        elif kind == "analysis":
            out.append(f"### 📊 日志分析  `{ts}`")
            out.append("")
            out.append(str(entry.get("text", "")))
        elif kind == "error":
            out.append(f"### ⚠ 错误  `{ts}`")
            out.append("")
            out.append(str(entry.get("text", "")))
        elif kind == "action_requested":
            out.append(f"### ⚙ 请求执行指令  `{ts}`")
            out.append("")
            out.append(f"- 动作：`{entry.get('name', '')}`")
            out.append("- 参数：")
            out.append("")
            out.append("```json")
            out.append(
                json.dumps(
                    entry.get("arguments", {}), ensure_ascii=False, indent=2, default=str
                )
            )
            out.append("```")
        elif kind == "action_result":
            out.append(f"### ✅ 指令执行结果  `{ts}`")
            out.append("")
            out.append(f"- 动作：`{entry.get('name', '')}`")
            out.append(f"- 状态：`{entry.get('status', '')}`")
            out.append(f"- 风险等级：`{entry.get('risk_level', '')}`")
            out.append(f"- 白名单自动执行：`{entry.get('auto_approved', False)}`")
            out.append(f"- 消息：{entry.get('message', '')}")
            out.append("- 结果：")
            out.append("")
            out.append("```json")
            out.append(
                json.dumps(
                    entry.get("result", {}), ensure_ascii=False, indent=2, default=str
                )
            )
            out.append("```")
        elif kind == "confirm_prompt":
            out.append(f"### ❓ 弹出确认卡片  `{ts}`")
            out.append("")
            out.append(f"- 动作：`{entry.get('name', '')}`")
            out.append(f"- 风险等级：`{entry.get('risk_level', '')}`")
            out.append(f"- 原因：{entry.get('reason', '')}")
            out.append("- 参数：")
            out.append("")
            out.append("```json")
            out.append(
                json.dumps(
                    entry.get("arguments", {}), ensure_ascii=False, indent=2, default=str
                )
            )
            out.append("```")
        elif kind == "confirm_decision":
            out.append(f"### 🖱 确认决定  `{ts}`")
            out.append("")
            out.append(f"- 动作：`{entry.get('name', '')}`")
            out.append(f"- 确认：`{entry.get('confirmed', False)}`")
            out.append(f"- 记住本会话：`{entry.get('remember_session', False)}`")
            out.append(f"- 加入白名单：`{entry.get('remember_resident', False)}`")
            out.append(f"- 卡片状态：{entry.get('status_text', '')}")
        elif kind == "context":
            out.append(f"### 📎 注入上下文（喂给模型的数据）  `{ts}`")
            out.append("")
            scope = str(entry.get("scope", "") or "")
            if scope:
                out.append(f"- 范围：{scope}")
            blocks = entry.get("blocks", []) or []
            out.append(f"- 数据块数量：{len(blocks)}")
            for block in blocks:
                out.append("")
                out.append(f"**{block.get('source', '上下文')}：**")
                out.append("")
                out.append("```text")
                out.append(str(block.get("text", "")))
                out.append("```")
        elif kind == "usage":
            out.append(f"### 📈 用量  `{ts}`")
            out.append("")
            out.append(
                f"- 本次：↑{entry.get('turn_prompt', 0)} ↓{entry.get('turn_completion', 0)} "
                f"tokens @ {entry.get('output_tps', 0)} tok/s"
            )
            out.append(
                f"- 会话累计：↑{entry.get('session_prompt', 0)} "
                f"↓{entry.get('session_completion', 0)} tokens "
                f"（{entry.get('requests', 0)} 次请求）"
            )
        else:
            out.append(f"### {kind}  `{ts}`")
            out.append("")
            out.append(
                "```json\n"
                + json.dumps(entry, ensure_ascii=False, indent=2, default=str)
                + "\n```"
            )
        out.append("")
        if step is not None and out and out[0].startswith("### "):
            out[0] = "#### " + f"步骤 {step} · " + out[0][len("### "):]
        return out

    def _read_audit_tail(self, max_lines: int = 50) -> str:
        try:
            from core.ai.actions.audit import get_audit_log

            path = get_audit_log().path
            if not os.path.isfile(path):
                return "_（无审计日志文件）_"
            with open(path, "r", encoding="utf-8") as f:
                tail = f.readlines()[-max_lines:]
            if not tail:
                return "_（审计日志为空）_"
            return "```jsonl\n" + "".join(tail).rstrip("\n") + "\n```"
        except Exception:
            logger.error("读取审计日志失败", exc_info=True)
            return "_（读取审计日志失败，请查看应用日志）_"

    def _on_send_clicked(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._input.clear()
        if self._waveform_provider_cb is not None:
            self._start_digest_send(text, via_button=False)
            return
        self._record("user", text=text)
        self._last_user_text = text
        self._chat.add_user_message(text)
        picked = self._take_picked_context()
        self._record_injected_context(picked=picked)
        self._service.send(text, extra_context=picked)

    def _on_analyze_clicked(self) -> None:
        level = self._level_combo.currentText()
        max_lines = min(self._lines_spin.value(), _MAX_LINES_CAP)
        self._record(
            "user", text=f"[Analyze Logs] level≥{level}, ≤{max_lines} lines per type"
        )
        self._chat.add_user_message(
            f"Analyze recent logs (level≥{level}, ≤{max_lines} lines per type)"
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
        label = "Test Script" if kind == SCRIPT_DRAFT else "Test Config"
        self._record("user", text=f"[Generate {label} Draft] {text}")
        self._chat.add_user_message(f"Generate {label} draft: {text}")
        self._input.clear()
        self._service.generate_draft(kind, text)

    def _on_draft_ready(self, parsed: ParsedResponse) -> None:
        if parsed is None:
            return
        if not parsed.ok or parsed.payload is None:
            errors = "; ".join(parsed.errors) if parsed.errors else "Draft parsing failed"
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

        dialog = ScriptPreviewDialog(draft, self._script_apply_cb, parent=self)
        if dialog.exec():
            self._chat.add_system_message("Test script draft applied to the canvas.")

    def _on_response(self, content: str) -> None:
        self._record("assistant", text=content or "")
        self._last_assistant_text = content or ""
        self._chat.add_ai_message(content)

    def _on_feedback(self, msg_id: str, rating: str) -> None:
        """👍/👎 反馈：转发给 service 采集（隐私开关关闭时静默）。"""
        try:
            self._service.record_feedback(msg_id, rating)
        except Exception:
            logger.error("提交反馈失败", exc_info=True)
        self._chat.add_system_message(
            "Thanks for the feedback." if rating == "up" else "Recorded, thanks for the feedback."
        )

    def _on_curate_requested(self, kind: str, _payload: str) -> None:
        """对话气泡⋯菜单：把当前这轮沉淀为对应资产（草稿生成走后台线程）。"""
        if not (self._last_user_text or self._last_assistant_text):
            self._chat.add_system_message("No conversation content available to curate.")
            return
        turn = {
            "user": self._last_user_text,
            "assistant": self._last_assistant_text,
            "page_key": self._service.current_page_key() or "",
        }
        self._chat.add_system_message("Generating curation draft…")
        self._start_curate(kind, turn)

    def _start_curate(self, kind: str, turn: dict) -> None:
        from PySide6.QtCore import QObject, QThread, Signal

        from core.ai.curator import Curator

        settings = self._service.settings

        class _DraftWorker(QObject):
            done = Signal(dict)
            failed = Signal(str)

            def run(self) -> None:
                try:
                    draft = Curator(settings).make_draft(turn, kind)
                    self.done.emit(draft or {})
                except Exception as exc:  # noqa: BLE001
                    self.failed.emit(str(exc))

        thread = QThread(self)
        worker = _DraftWorker()
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.done.connect(lambda d: self._on_draft_made(kind, turn, d))
        worker.failed.connect(
            lambda m: self._chat.add_system_message(f"Draft generation failed: {m}")
        )
        worker.done.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._curate_thread = thread
        self._curate_worker = worker
        thread.start()

    def _on_draft_made(self, kind: str, turn: dict, draft: dict) -> None:
        from ui.ai.curate_dialog import CurateDialog
        from core.ai.curator import Curator

        if not draft:
            self._chat.add_system_message("Draft is empty, curation cancelled.")
            return
        dialog = CurateDialog(kind, draft, parent=self)
        if not dialog.exec():
            self._chat.add_system_message("Curation cancelled.")
            return
        final_draft = dialog.result_draft()
        curator = Curator(self._service.settings)
        ok = {
            "nudge": curator.as_nudge,
            "quick_action": curator.as_quick_action,
            "project_rule": curator.as_project_rule,
            "eval_case": curator.as_eval_case,
        }.get(kind, lambda _d: False)(final_draft)
        if ok:
            self._chat.add_system_message("Curated and applied immediately.")
            self.refresh_quick_actions()
            if self._service.settings.telemetry_enabled:
                self._service._record_telemetry(
                    "curated", {"kind": kind, "src": final_draft.get("_src", "")}
                )
        else:
            self._chat.add_system_message("Failed to write curation, please check the logs.")

    def _on_analysis(self, result) -> None:
        self._record("analysis", text=str(getattr(result, "summary", "") or result))
        self._chat.add_analysis_message(result)

    def _on_error(self, message: str) -> None:
        self._chat.discard_stream_message()
        self._record("error", text=message)
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
