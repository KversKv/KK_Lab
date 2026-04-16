from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar,
)


_LOG_FRAME_STYLE = """
    QFrame#logContainer {
        background-color: #09142e;
        border: 1px solid #1a2d57;
        border-radius: 16px;
    }
    QFrame#logContainer QLabel#sectionTitle {
        font-size: 12px;
        font-weight: 700;
        color: #f4f7ff;
        background-color: transparent;
    }
    QFrame#logContainer QLabel#fieldLabel {
        color: #8eb0e3;
        font-size: 11px;
        background-color: transparent;
    }
    QFrame#logContainer QPushButton#smallActionBtn {
        min-height: 34px;
        padding: 6px 10px;
        border-radius: 10px;
        background-color: #13254b;
        color: #dce7ff;
    }
    QFrame#logContainer QTextEdit#logEdit {
        background-color: #061022;
        border: 1px solid #1f315d;
        border-radius: 8px;
        color: #7cecc8;
        font-family: Consolas, "Courier New", monospace;
        font-size: 11px;
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
"""


class ExecutionLogsFrame(QFrame):

    def __init__(self, title="⊙ Execution Logs", show_progress=True, parent=None):
        super().__init__(parent)
        self.setObjectName("logContainer")
        self._show_progress = show_progress
        self.setStyleSheet(_LOG_FRAME_STYLE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.log_title = QLabel(title)
        self.log_title.setObjectName("sectionTitle")
        header.addWidget(self.log_title)
        header.addStretch()

        if show_progress:
            self.progress_text_label = QLabel("0% Complete")
            self.progress_text_label.setObjectName("fieldLabel")
            header.addWidget(self.progress_text_label)

            self.progress_bar = QProgressBar()
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setTextVisible(False)
            self.progress_bar.setFixedWidth(120)
            header.addWidget(self.progress_bar)

        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.setObjectName("smallActionBtn")
        header.addWidget(self.clear_log_btn)

        layout.addLayout(header)

        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("logEdit")
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(120)
        layout.addWidget(self.log_edit)

        self.clear_log_btn.clicked.connect(self.clear_log)

    def append_log(self, message: str):
        self.log_edit.append(message)
        self.log_edit.verticalScrollBar().setValue(
            self.log_edit.verticalScrollBar().maximum()
        )

    def clear_log(self):
        self.log_edit.clear()

    def set_progress(self, value: int):
        if not self._show_progress:
            return
        value = max(0, min(100, int(value)))
        self.progress_bar.setValue(value)
        self.progress_text_label.setText(f"{value}% Complete")
