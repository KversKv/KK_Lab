"""Template gallery dialog for Custom Test."""

from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from core.custom_test.paths import iter_template_files, load_recent_sequences
from core.custom_test.serialization import load_sequence_file
from log_config import get_logger

logger = get_logger(__name__)


class TemplateGalleryDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Custom Test Templates")
        self.resize(520, 420)
        self.selected_path: Optional[str] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._hint = QLabel("Templates and recent sequences")
        self._hint.setStyleSheet("QLabel { color: #8ea8d4; font-size: 12px; }")
        layout.addWidget(self._hint)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.itemDoubleClicked.connect(self._accept_item)
        layout.addWidget(self._list, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_current)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()

    def _populate(self) -> None:
        self._list.clear()
        self._add_group("Templates", iter_template_files())
        self._add_group("Recent", load_recent_sequences())

    def _add_group(self, label: str, paths) -> None:
        paths = list(paths)
        if not paths:
            return
        header = QListWidgetItem(label)
        header.setFlags(Qt.NoItemFlags)
        self._list.addItem(header)
        for path in paths:
            item = QListWidgetItem(self._describe(path))
            item.setData(Qt.UserRole, path)
            self._list.addItem(item)

    def _describe(self, path: str) -> str:
        name = os.path.basename(path)
        try:
            doc = load_sequence_file(path)
            caps = ", ".join(doc.metadata.get("required_capabilities", [])[:3])
            suffix = f"{len(doc.nodes)} nodes"
            if caps:
                suffix = f"{suffix} | {caps}"
            return f"{name}    {suffix}"
        except Exception as exc:
            logger.warning("Template metadata load failed: %s", exc)
            return name

    def _accept_item(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.UserRole)
        if path:
            self.selected_path = str(path)
            self.accept()

    def _accept_current(self) -> None:
        current = self._list.currentItem()
        if current is None:
            return
        self._accept_item(current)
