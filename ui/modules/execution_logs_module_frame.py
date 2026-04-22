#python -m ui.modules.execution_logs_module_frame
import os
import time
from datetime import datetime

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar, QLineEdit,
    QMenu, QApplication, QFileDialog, QWidget,
)
from PySide6.QtCore import Qt, QTimer, QRectF, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtSvg import QSvgRenderer


_SVG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "resources", "modules", "SVG_Logs",
)


def _tinted_svg_icon(svg_path: str, color: str, size: int = 14) -> QIcon:
    if not os.path.isfile(svg_path):
        return QIcon()
    renderer = QSvgRenderer(svg_path)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(color))
    painter.end()
    return QIcon(pixmap)


_LEVEL_COLORS = {
    "START": "#4ade80",
    "DONE":  "#4ade80",
    "PASS":  "#4ade80",
    "STEP":  "#60a5fa",
    "INFO":  "#60a5fa",
    "SYSTEM":"#60a5fa",
    "WARN":  "#facc15",
    "WARNING":"#facc15",
    "ERROR": "#f87171",
    "FAIL":  "#f87171",
    "STOP":  "#f87171",
    "USER":  "#c084fc",
    "EXPORT":"#38bdf8",
    "TEMPLATE":"#38bdf8",
}

_DEFAULT_LOG_COLOR = "#7cecc8"

_COLLAPSED_HEIGHT = 30
_DEFAULT_HEIGHT = 200

_LOG_FRAME_STYLE = """
    QFrame#logContainer {
        background-color: #09142e;
        border: 1px solid #1a2d57;
        border-radius: 14px;
    }
    QFrame#logContainer QLabel#sectionTitle {
        font-size: 11px;
        font-weight: 700;
        color: #f4f7ff;
        background-color: transparent;
        padding: 0px;
        margin: 0px;
    }
    QFrame#logContainer QLabel#fieldLabel {
        color: #8eb0e3;
        font-size: 11px;
        background-color: transparent;
    }
    QFrame#logContainer QLabel#statusLabel {
        color: #6b83b0;
        font-size: 10px;
        background-color: transparent;
    }
    QFrame#logContainer QPushButton#smallActionBtn {
        min-height: 0px;
        max-height: 20px;
        padding: 2px 8px;
        border-radius: 6px;
        background-color: #13254b;
        color: #dce7ff;
        font-size: 10px;
        border: none;
    }
    QFrame#logContainer QPushButton#smallActionBtn:hover {
        background-color: #1C2D55;
    }
    QFrame#logContainer QPushButton#smallActionBtn:pressed {
        background-color: #102040;
    }
    QFrame#logContainer QPushButton#smallActionBtn:checked {
        background-color: #1e3a6d;
        border: 1px solid #3b6bcf;
    }
    QFrame#logContainer QTextEdit#logEdit {
        background-color: #061022;
        border: 1px solid #1f315d;
        border-radius: 8px;
        color: #7cecc8;
        font-family: Consolas, "Courier New", monospace;
        font-size: 11px;
        padding: 6px 8px;
    }
    QFrame#logContainer QProgressBar {
        background-color: #152749;
        border: none;
        border-radius: 4px;
        text-align: center;
        color: #b7c8ea;
        min-height: 8px;
        max-height: 8px;
    }
    QFrame#logContainer QProgressBar::chunk {
        background-color: #5b5cf6;
        border-radius: 4px;
    }
    QFrame#logContainer QLineEdit#filterInput {
        background-color: #0b1a38;
        border: 1px solid #1f315d;
        border-radius: 6px;
        color: #c8d8f0;
        font-size: 10px;
        padding: 2px 6px;
        min-height: 18px;
        max-height: 18px;
    }
    QFrame#logContainer QLineEdit#filterInput:focus {
        border: 1px solid #3b6bcf;
    }
    QFrame#logContainer QMenu {
        background-color: #0d1f42;
        border: 1px solid #1f315d;
        border-radius: 6px;
        padding: 4px;
        color: #c8d8f0;
        font-size: 10px;
    }
    QFrame#logContainer QMenu::item {
        padding: 4px 16px;
        border-radius: 4px;
    }
    QFrame#logContainer QMenu::item:selected {
        background-color: #1C2D55;
    }
    QFrame#logContainer QMenu::separator {
        height: 1px;
        background: #1f315d;
        margin: 2px 8px;
    }
"""


def _parse_level(message: str) -> str:
    start = message.find("[")
    if start == -1:
        return ""
    end = message.find("]", start)
    if end == -1:
        return ""
    return message[start + 1:end].strip().upper()


class ExecutionLogsFrame(QFrame):

    log_exported = Signal(str)

    def __init__(self, title="Logs", show_progress=True, parent=None):
        super().__init__(parent)
        self.setObjectName("logContainer")
        self._show_progress = show_progress
        self.setStyleSheet(_LOG_FRAME_STYLE)

        self._all_logs = []
        self._auto_scroll = True
        self._active_level_filter = "ALL"
        self._keyword_filter = ""
        self._filter_visible = False
        self._start_time = None
        self._current_step_text = ""
        self._total_steps = 0
        self._current_step_index = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._header_widget = QWidget()
        self._header_widget.setStyleSheet("background: transparent;")
        header_layout = QVBoxLayout(self._header_widget)
        header_layout.setContentsMargins(12, 8, 12, 6)
        header_layout.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.setSpacing(6)

        svg_path = os.path.join(_SVG_DIR, "logs.svg")
        title_icon = _tinted_svg_icon(svg_path, "#8eb0e3", 14)
        if not title_icon.isNull():
            icon_label = QLabel()
            icon_label.setPixmap(title_icon.pixmap(14, 14))
            icon_label.setFixedSize(16, 16)
            icon_label.setStyleSheet("background: transparent;")
            toolbar.addWidget(icon_label)

        self.log_title = QLabel(title)
        self.log_title.setObjectName("sectionTitle")
        toolbar.addWidget(self.log_title)

        toolbar.addStretch()

        self.filter_btn = self._make_toolbar_btn(
            os.path.join(_SVG_DIR, "filter.svg"), "过滤"
        )
        self.filter_btn.setCheckable(True)
        self.filter_btn.clicked.connect(self._toggle_filter)
        toolbar.addWidget(self.filter_btn)

        self.level_btn = self._make_toolbar_btn(
            os.path.join(_SVG_DIR, "info.svg"), "All ▾"
        )
        self._level_menu = QMenu(self)
        for lvl in ["ALL", "START", "STEP", "INFO", "WARN", "ERROR"]:
            action = QAction(lvl, self)
            action.triggered.connect(lambda checked, l=lvl: self._set_level_filter(l))
            self._level_menu.addAction(action)
        self.level_btn.setMenu(self._level_menu)
        toolbar.addWidget(self.level_btn)

        self.copy_btn = self._make_toolbar_btn(
            os.path.join(_SVG_DIR, "copy.svg"), "复制"
        )
        self.copy_btn.clicked.connect(self._copy_logs)
        toolbar.addWidget(self.copy_btn)

        self.export_btn = self._make_toolbar_btn(
            os.path.join(_SVG_DIR, "export.svg"), "导出"
        )
        self.export_btn.clicked.connect(self._export_logs)
        toolbar.addWidget(self.export_btn)

        if show_progress:
            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setMinimumWidth(60)
            self.progress_bar.setMaximumWidth(120)
            toolbar.addWidget(self.progress_bar)

            self.progress_text_label = QLabel("0%")
            self.progress_text_label.setObjectName("fieldLabel")
            self.progress_text_label.setFixedWidth(32)
            toolbar.addWidget(self.progress_text_label)

        self.clear_log_btn = self._make_toolbar_btn(
            os.path.join(_SVG_DIR, "trash.svg"), "清除"
        )
        self.clear_log_btn.clicked.connect(self.clear_log)
        toolbar.addWidget(self.clear_log_btn)

        header_layout.addLayout(toolbar)

        self._filter_row = QWidget()
        self._filter_row.setStyleSheet("background: transparent;")
        self._filter_row.setVisible(False)
        filter_layout = QHBoxLayout(self._filter_row)
        filter_layout.setContentsMargins(0, 2, 0, 0)
        filter_layout.setSpacing(6)

        self._filter_input = QLineEdit()
        self._filter_input.setObjectName("filterInput")
        self._filter_input.setPlaceholderText("输入关键词过滤日志...")
        self._filter_input.textChanged.connect(self._on_keyword_changed)
        filter_layout.addWidget(self._filter_input)

        header_layout.addWidget(self._filter_row)

        if show_progress:
            self._status_row = QWidget()
            self._status_row.setStyleSheet("background: transparent;")
            status_layout = QHBoxLayout(self._status_row)
            status_layout.setContentsMargins(0, 0, 0, 0)
            status_layout.setSpacing(12)

            self._elapsed_label = QLabel("运行: --:--")
            self._elapsed_label.setObjectName("statusLabel")
            status_layout.addWidget(self._elapsed_label)

            self._step_label = QLabel("步骤: -/-")
            self._step_label.setObjectName("statusLabel")
            status_layout.addWidget(self._step_label)

            self._eta_label = QLabel("剩余: --:--")
            self._eta_label.setObjectName("statusLabel")
            status_layout.addWidget(self._eta_label)

            status_layout.addStretch()

            self._scroll_lock_btn = self._make_toolbar_btn(
                os.path.join(_SVG_DIR, "auto-scroll.svg"), "自动滚动"
            )
            self._scroll_lock_btn.setCheckable(True)
            self._scroll_lock_btn.setChecked(True)
            self._scroll_lock_btn.clicked.connect(self._on_scroll_lock_toggled)
            status_layout.addWidget(self._scroll_lock_btn)

            header_layout.addWidget(self._status_row)

            self._elapsed_timer = QTimer(self)
            self._elapsed_timer.setInterval(1000)
            self._elapsed_timer.timeout.connect(self._update_elapsed)

        root.addWidget(self._header_widget)

        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("logEdit")
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(40)
        root.addWidget(self.log_edit)

        if self.log_edit.verticalScrollBar():
            self.log_edit.verticalScrollBar().valueChanged.connect(
                self._on_user_scroll
            )

    def _make_toolbar_btn(self, svg_path: str, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("smallActionBtn")
        btn.setCursor(Qt.PointingHandCursor)
        icon = _tinted_svg_icon(svg_path, "#8eb0e3", 12)
        if not icon.isNull():
            btn.setIcon(icon)
        return btn

    def _toggle_filter(self, checked: bool):
        self._filter_visible = checked
        self._filter_row.setVisible(checked)
        if not checked:
            self._filter_input.clear()

    def _set_level_filter(self, level: str):
        self._active_level_filter = level
        display = "All ▾" if level == "ALL" else f"{level} ▾"
        self.level_btn.setText(display)
        self._apply_filter()

    def _on_keyword_changed(self, text: str):
        self._keyword_filter = text.strip()
        self._apply_filter()

    def _apply_filter(self):
        self.log_edit.clear()
        for raw_msg, html_line in self._all_logs:
            if self._matches_filter(raw_msg):
                self.log_edit.append(html_line)
        if self._auto_scroll:
            self._scroll_to_bottom()

    def _matches_filter(self, raw_msg: str) -> bool:
        if self._active_level_filter != "ALL":
            lvl = _parse_level(raw_msg)
            if lvl != self._active_level_filter:
                return False
        if self._keyword_filter:
            if self._keyword_filter.lower() not in raw_msg.lower():
                return False
        return True

    def _copy_logs(self):
        clipboard = QApplication.clipboard()
        if clipboard:
            plain = "\n".join(raw for raw, _ in self._all_logs)
            clipboard.setText(plain)

    def _export_logs(self):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"logs_{ts}.txt"
        path, _ = QFileDialog.getSaveFileName(
            self, "导出日志", default_name, "Text Files (*.txt);;All Files (*)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    for raw, _ in self._all_logs:
                        f.write(raw + "\n")
                self.log_exported.emit(path)
            except Exception:
                pass

    def _on_scroll_lock_toggled(self, checked: bool):
        self._auto_scroll = checked

    def _on_user_scroll(self, value: int):
        sb = self.log_edit.verticalScrollBar()
        if sb and sb.maximum() > 0:
            at_bottom = value >= sb.maximum() - 5
            if not at_bottom and self._auto_scroll:
                self._auto_scroll = False
                if self._show_progress and hasattr(self, "_scroll_lock_btn"):
                    self._scroll_lock_btn.setChecked(False)
            elif at_bottom and not self._auto_scroll:
                self._auto_scroll = True
                if self._show_progress and hasattr(self, "_scroll_lock_btn"):
                    self._scroll_lock_btn.setChecked(True)

    def _scroll_to_bottom(self):
        sb = self.log_edit.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _format_html(self, message: str) -> str:
        ts = datetime.now().strftime("%H:%M:%S")
        level = _parse_level(message)
        color = _LEVEL_COLORS.get(level, _DEFAULT_LOG_COLOR)
        escaped = (
            message
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        return (
            f'<span style="color:#4a5e82;">{ts}</span> '
            f'<span style="color:{color};">{escaped}</span>'
        )

    def append_log(self, message: str):
        html = self._format_html(message)
        self._all_logs.append((message, html))

        if self._matches_filter(message):
            self.log_edit.append(html)
            if self._auto_scroll:
                self._scroll_to_bottom()

    def clear_log(self):
        self._all_logs.clear()
        self.log_edit.clear()

    def set_progress(self, value: int):
        if not self._show_progress:
            return
        value = max(0, min(100, int(value)))
        self.progress_bar.setValue(value)
        self.progress_text_label.setText(f"{value}%")

    def start_timer(self, total_steps: int = 0):
        if not self._show_progress:
            return
        self._start_time = time.monotonic()
        self._total_steps = total_steps
        self._current_step_index = 0
        self._elapsed_timer.start()
        self._update_elapsed()

    def stop_timer(self):
        if not self._show_progress:
            return
        if hasattr(self, "_elapsed_timer"):
            self._elapsed_timer.stop()

    def update_step(self, index: int, text: str = ""):
        if not self._show_progress:
            return
        self._current_step_index = index
        self._current_step_text = text
        total = self._total_steps or 1
        self._step_label.setText(f"步骤: {index}/{total}")
        self._update_eta()

    def _update_elapsed(self):
        if not self._start_time:
            return
        elapsed = time.monotonic() - self._start_time
        m, s = divmod(int(elapsed), 60)
        h, m = divmod(m, 60)
        if h > 0:
            self._elapsed_label.setText(f"运行: {h:d}:{m:02d}:{s:02d}")
        else:
            self._elapsed_label.setText(f"运行: {m:02d}:{s:02d}")
        self._update_eta()

    def _update_eta(self):
        if not self._start_time or not self._total_steps or self._current_step_index <= 0:
            self._eta_label.setText("剩余: --:--")
            return
        elapsed = time.monotonic() - self._start_time
        per_step = elapsed / self._current_step_index
        remaining_steps = self._total_steps - self._current_step_index
        eta = per_step * remaining_steps
        m, s = divmod(int(eta), 60)
        h, m = divmod(m, 60)
        if h > 0:
            self._eta_label.setText(f"剩余: {h:d}:{m:02d}:{s:02d}")
        else:
            self._eta_label.setText(f"剩余: {m:02d}:{s:02d}")


if __name__ == "__main__":
    #python -m ui.modules.execution_logs_module_frame
    import sys
    from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout

    DARK_BG_STYLE = """
        QWidget {
            background-color: #020817;
            color: #dbe7ff;
        }
    """

    class _DemoWidget(QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setStyleSheet(DARK_BG_STYLE)

            root = QVBoxLayout(self)
            root.setContentsMargins(12, 12, 12, 12)
            root.setSpacing(12)

            self.logs_with_progress = ExecutionLogsFrame(
                title="Execution Logs", show_progress=True
            )
            self.logs_with_progress.setMinimumHeight(_DEFAULT_HEIGHT)
            root.addWidget(self.logs_with_progress)

            self.logs_no_progress = ExecutionLogsFrame(
                title="Execution Logs (no progress)", show_progress=False
            )
            root.addWidget(self.logs_no_progress)

            root.addStretch()

            self.logs_with_progress.start_timer(total_steps=10)
            sample_logs = [
                "[START] ▶ 开始执行序列，共 10 步",
                "[STEP]  ↻ Loop(Range) 迭代 1/13: i=0.1",
                "[STEP]    ⚡ N6705C Set Voltage CH4=0.1V  ✓",
                "[INFO] 仪器已连接: N6705C @ 192.168.1.10",
                "[WARN] 温度传感器响应延迟 200ms",
                "[ERROR] 通信超时: DSOX4034A",
                "[STEP]  ↻ Loop(Range) 迭代 2/13: i=0.2",
                "[STEP]    ⚡ N6705C Set Voltage CH4=0.2V  ✓",
                "[DONE] 执行完成，记录 13 行数据",
            ]
            for i, msg in enumerate(sample_logs):
                self.logs_with_progress.append_log(msg)
            self.logs_with_progress.set_progress(23)
            self.logs_with_progress.update_step(3, "N6705C Set Voltage")

            self.logs_no_progress.append_log("[SYSTEM] No progress bar variant.")
            self.logs_no_progress.append_log("[INFO] Log only mode.")
            self.logs_no_progress.append_log("[WARN] This is a warning.")
            self.logs_no_progress.append_log("[ERROR] This is an error.")

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    w = _DemoWidget()
    w.setWindowTitle("Execution Logs Module Frame Demo")
    w.setFixedSize(700, 550)
    w.show()
    w.move(100, 200)

    sys.exit(app.exec())
