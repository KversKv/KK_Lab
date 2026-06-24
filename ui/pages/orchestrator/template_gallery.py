"""Template gallery dialog for Orchestrator."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.orchestrator.paths import iter_template_files, load_recent_sequences
from core.orchestrator.serialization import load_sequence_file
from log_config import get_logger
from ui.theme import Colors, FontSizes, Radius
from ui.widgets.scrollbar import SCROLLBAR_STYLE

logger = get_logger(__name__)


@dataclass(frozen=True)
class _TemplateEntry:
    path: str
    group: str
    name: str = ""
    node_count: int = 0
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    error: str = ""

    @property
    def search_text(self) -> str:
        return " ".join((self.name, self.group, self.path, " ".join(self.capabilities))).lower()


_DIALOG_QSS = f"""
    QDialog#templateGalleryDialog {{
        background-color: {Colors.bg_primary};
        color: {Colors.text_secondary};
    }}
    QLabel {{
        background: transparent;
        border: none;
        color: {Colors.text_secondary};
    }}
    QLabel#dialogTitle {{
        color: {Colors.text_primary};
        font-size: {FontSizes.title};
        font-weight: 700;
    }}
    QLabel#dialogSubtitle {{
        color: {Colors.text_accent};
        font-size: {FontSizes.caption};
    }}
    QLabel#summaryLabel {{
        color: {Colors.text_dim};
        font-size: {FontSizes.caption};
    }}
    QLabel#emptyLabel {{
        color: {Colors.text_disabled};
        font-size: {FontSizes.body};
    }}
    QFrame#headerCard {{
        background-color: {Colors.bg_panel};
        border: 1px solid {Colors.border_primary};
        border-radius: {Radius.card}px;
    }}
    QLineEdit#templateSearch {{
        background-color: {Colors.bg_input};
        border: 1px solid {Colors.border_input};
        border-radius: {Radius.widget}px;
        color: {Colors.text_secondary};
        padding: 7px 10px;
        selection-background-color: {Colors.accent_soft};
    }}
    QLineEdit#templateSearch:focus {{
        border: 1px solid {Colors.accent_primary};
    }}
    QListWidget#templateList {{
        background-color: {Colors.bg_secondary};
        border: 1px solid {Colors.border_secondary};
        border-radius: {Radius.card}px;
        outline: none;
        padding: 6px;
    }}
    QListWidget#templateList::item {{
        background: transparent;
        border: none;
        margin: 3px 2px;
    }}
    QListWidget#templateList::item:selected {{
        background: transparent;
    }}
    QFrame#templateItem {{
        background-color: {Colors.bg_card};
        border: 1px solid {Colors.border_primary};
        border-radius: {Radius.widget}px;
    }}
    QFrame#templateItem:hover {{
        background-color: #0f1d3a;
        border: 1px solid #27406f;
    }}
    QFrame#templateItem[selected="true"] {{
        background-color: #111f47;
        border: 1px solid {Colors.accent_primary};
    }}
    QLabel#itemName {{
        color: {Colors.text_primary};
        font-size: {FontSizes.body};
        font-weight: 700;
    }}
    QLabel#itemBadge {{
        background-color: {Colors.accent_soft};
        color: #cfd6ff;
        border: 1px solid {Colors.border_accent};
        border-radius: {Radius.small}px;
        padding: 2px 7px;
        font-size: {FontSizes.tiny};
        font-weight: 700;
    }}
    QLabel#itemMeta {{
        color: {Colors.text_accent};
        font-size: {FontSizes.caption};
    }}
    QLabel#itemPath {{
        color: {Colors.text_disabled};
        font-size: {FontSizes.tiny};
    }}
    QLabel#capabilityChip {{
        background-color: #0b2336;
        color: #87d7ff;
        border: 1px solid #16415f;
        border-radius: {Radius.small}px;
        padding: 2px 6px;
        font-size: {FontSizes.tiny};
    }}
    QLabel#warningChip {{
        background-color: #321923;
        color: {Colors.error};
        border: 1px solid #5b2638;
        border-radius: {Radius.small}px;
        padding: 2px 6px;
        font-size: {FontSizes.tiny};
    }}
    QPushButton {{
        background-color: {Colors.bg_card};
        border: 1px solid {Colors.border_accent};
        border-radius: {Radius.widget}px;
        color: {Colors.text_secondary};
        min-width: 76px;
        min-height: 28px;
        padding: 4px 14px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: {Colors.submenu_item_hover_bg};
        border: 1px solid #3a5a9f;
    }}
    QPushButton:pressed {{
        background-color: {Colors.bg_input};
    }}
    QPushButton:disabled {{
        background-color: {Colors.disabled_btn_bg};
        border: 1px solid {Colors.disabled_btn_border};
        color: {Colors.disabled_text};
    }}
    QPushButton#openButton {{
        background-color: {Colors.accent_primary};
        border: 1px solid {Colors.accent_hover};
        color: #ffffff;
    }}
    QPushButton#openButton:hover {{
        background-color: {Colors.accent_hover};
    }}
    QPushButton#openButton:pressed {{
        background-color: {Colors.accent_pressed};
    }}
""" + SCROLLBAR_STYLE


def _compact_chip_text(text: str, max_chars: int = 24) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars - 1]}..."


class _TemplateItemWidget(QFrame):
    def __init__(self, entry: _TemplateEntry, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._list: QListWidget | None = None
        self._item: QListWidgetItem | None = None
        self.setObjectName("templateItem")
        self.setProperty("selected", False)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMinimumHeight(76)
        self.setCursor(Qt.PointingHandCursor)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 9, 12, 9)
        root.setSpacing(6)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        badge = QLabel(entry.group)
        badge.setObjectName("itemBadge")
        badge.setAlignment(Qt.AlignCenter)
        badge.setMinimumWidth(64)
        title_row.addWidget(badge, 0, Qt.AlignTop)

        name_label = QLabel(_compact_chip_text(entry.name, 48))
        name_label.setObjectName("itemName")
        name_label.setToolTip(entry.name)
        name_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        title_row.addWidget(name_label, 1)
        root.addLayout(title_row)

        meta_row = QHBoxLayout()
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)

        node_label = QLabel(f"{entry.node_count} node{'s' if entry.node_count != 1 else ''}")
        node_label.setObjectName("itemMeta")
        meta_row.addWidget(node_label)

        visible_capabilities = entry.capabilities[:2]
        for capability in visible_capabilities:
            chip = QLabel(_compact_chip_text(capability))
            chip.setObjectName("capabilityChip")
            chip.setToolTip(capability)
            chip.setMaximumWidth(180)
            meta_row.addWidget(chip)
        hidden_count = len(entry.capabilities) - len(visible_capabilities)
        if hidden_count > 0:
            chip = QLabel(f"+{hidden_count}")
            chip.setObjectName("capabilityChip")
            chip.setToolTip(", ".join(entry.capabilities[2:]))
            meta_row.addWidget(chip)
        if entry.error:
            warning = QLabel("metadata unavailable")
            warning.setObjectName("warningChip")
            meta_row.addWidget(warning)
        meta_row.addStretch(1)
        root.addLayout(meta_row)

        path_label = QLabel(os.path.normpath(entry.path))
        path_label.setObjectName("itemPath")
        path_label.setWordWrap(True)
        root.addWidget(path_label)

        for label in self.findChildren(QLabel):
            label.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def bind_item(self, list_widget: QListWidget, item: QListWidgetItem) -> None:
        self._list = list_widget
        self._item = item

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event) -> None:
        if self._list is not None and self._item is not None and event.button() == Qt.LeftButton:
            self._list.setCurrentItem(self._item)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._list is not None and self._item is not None and event.button() == Qt.LeftButton:
            self._list.setCurrentItem(self._item)
            self._list.itemDoubleClicked.emit(self._item)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class TemplateGalleryDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("templateGalleryDialog")
        self.setWindowTitle("Orchestrator Templates")
        self.resize(760, 520)
        self.setMinimumSize(620, 440)
        self.setStyleSheet(_DIALOG_QSS)
        self.selected_path: Optional[str] = None
        self._entries: list[_TemplateEntry] = []
        self._item_widgets: list[tuple[QListWidgetItem, _TemplateItemWidget]] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        header = QFrame()
        header.setObjectName("headerCard")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(7)

        title = QLabel("Orchestrator Templates")
        title.setObjectName("dialogTitle")
        header_layout.addWidget(title)

        subtitle = QLabel("Open a saved template or pick from your recent Orchestrator sequences.")
        subtitle.setObjectName("dialogSubtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle)

        self._search = QLineEdit()
        self._search.setObjectName("templateSearch")
        self._search.setPlaceholderText("Search templates, capabilities or file path...")
        self._search.textChanged.connect(self._apply_filter)
        header_layout.addWidget(self._search)

        self._summary = QLabel()
        self._summary.setObjectName("summaryLabel")
        header_layout.addWidget(self._summary)

        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setObjectName("templateList")
        self._list.setAlternatingRowColors(False)
        self._list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._list.setSelectionMode(QAbstractItemView.SingleSelection)
        self._list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setSpacing(4)
        self._list.itemSelectionChanged.connect(self._sync_selection_style)
        self._list.itemDoubleClicked.connect(self._accept_item)
        layout.addWidget(self._list, 1)

        self._empty_label = QLabel("No templates found.")
        self._empty_label.setObjectName("emptyLabel")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.hide()
        layout.addWidget(self._empty_label, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Open | QDialogButtonBox.StandardButton.Cancel
        )
        self._open_btn = buttons.button(QDialogButtonBox.StandardButton.Open)
        self._cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        self._open_btn.setObjectName("openButton")
        self._open_btn.setDefault(True)
        self._open_btn.setAutoDefault(True)
        self._open_btn.setEnabled(False)
        self._cancel_btn.setDefault(False)
        self._cancel_btn.setAutoDefault(False)
        buttons.accepted.connect(self._accept_current)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._populate()

    def _populate(self) -> None:
        self._entries = []
        self._entries.extend(self._load_group("Template", iter_template_files()))
        self._entries.extend(self._load_group("Recent", load_recent_sequences()))

        self._list.clear()
        self._item_widgets.clear()
        for entry in self._entries:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, entry.path)
            item.setData(Qt.UserRole + 1, entry.search_text)
            widget = _TemplateItemWidget(entry, self._list)
            widget.bind_item(self._list, item)
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)
            self._item_widgets.append((item, widget))
        self._apply_filter(self._search.text())

    def _load_group(self, label: str, paths) -> list[_TemplateEntry]:
        return [self._build_entry(path, label) for path in paths]

    def _build_entry(self, path: str, label: str) -> _TemplateEntry:
        name = os.path.basename(path)
        try:
            doc = load_sequence_file(path)
            caps = tuple(str(capability) for capability in doc.metadata.get("required_capabilities", []))
            return _TemplateEntry(
                path=path,
                group=label,
                name=name,
                node_count=len(doc.nodes),
                capabilities=caps,
            )
        except Exception as exc:
            logger.warning("Template metadata load failed: %s", exc)
            return _TemplateEntry(path=path, group=label, name=name, error=str(exc))

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        visible_count = 0
        for row in range(self._list.count()):
            item = self._list.item(row)
            haystack = str(item.data(Qt.UserRole + 1) or "")
            visible = not needle or needle in haystack
            item.setHidden(not visible)
            if visible:
                visible_count += 1

        self._summary.setText(self._format_summary(visible_count))
        self._empty_label.setVisible(visible_count == 0)
        self._list.setVisible(visible_count > 0)

        if visible_count == 0:
            self._open_btn.setEnabled(False)
            return

        current = self._list.currentItem()
        if current is None or current.isHidden():
            self._select_first_visible()
        else:
            self._open_btn.setEnabled(bool(current.data(Qt.UserRole)))
        self._sync_selection_style()

    def _format_summary(self, visible_count: int) -> str:
        template_count = sum(1 for entry in self._entries if entry.group == "Template")
        recent_count = sum(1 for entry in self._entries if entry.group == "Recent")
        if visible_count == len(self._entries):
            return f"{template_count} templates | {recent_count} recent sequences"
        return f"{visible_count} matches | {template_count} templates | {recent_count} recent sequences"

    def _select_first_visible(self) -> None:
        for row in range(self._list.count()):
            item = self._list.item(row)
            if not item.isHidden():
                self._list.setCurrentItem(item)
                self._open_btn.setEnabled(bool(item.data(Qt.UserRole)))
                return
        self._list.setCurrentItem(None)
        self._open_btn.setEnabled(False)

    def _sync_selection_style(self) -> None:
        current = self._list.currentItem()
        self._open_btn.setEnabled(bool(current and current.data(Qt.UserRole)))
        for item, widget in self._item_widgets:
            widget.set_selected(item is current)

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
