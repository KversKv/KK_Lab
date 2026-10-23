# -*- coding: utf-8 -*-
"""快捷命令控件：_QuickCmdPreviewPopup / _QuickCmdButton / _ProjectTabBar / _QuickCommandPickerPopup（原 serialCom_module_frame.py 拆出）。"""

import os

from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabBar,
    QToolButton,
    QVBoxLayout,
)
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFont,
)
from PySide6.QtCore import (
    QMimeData,
    QPoint,
    QSize,
    QTimer,
    Qt,
    Signal,
)
from ui.utils.icon_utils import tinted_svg_icon as _tinted_svg_icon
from ui.modules.serialCom_module.serial_style import (
    _CLR_BG_CARD,
    _CLR_BORDER,
    _CLR_BORDER_HOVER,
    _CLR_ERROR,
    _CLR_FILTER_BORDER,
    _CLR_INPUT_BG,
    _CLR_SELECTION_BG,
    _CLR_SEND_BG,
    _CLR_TEXT_BTN_LOG,
    _CLR_TEXT_MUTED,
    _CLR_TEXT_TITLE,
    _SVG_LOGS_DIR,
    _SVG_SERIAL_DIR,
    _UI_FONT,
    quick_action_overlay_container_style,
    quick_action_overlay_style,
    quick_preview_popup_shadow,
    quick_preview_popup_style,
)

class _QuickCmdPreviewPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setObjectName("quickCmdPreviewPopupWindow")
        self._card = QFrame(self)
        self._card.setObjectName("quickCmdPreviewPopup")
        self._badge_label = QLabel("QUICK CMD")
        self._badge_label.setObjectName("quickCmdPreviewBadge")
        self._title_label = QLabel()
        self._title_label.setObjectName("quickCmdPreviewTitle")
        self._title_label.setTextFormat(Qt.PlainText)
        self._content_label = QLabel()
        self._content_label.setObjectName("quickCmdPreviewContent")
        self._content_label.setWordWrap(True)
        self._content_label.setTextFormat(Qt.PlainText)
        self._content_label.setTextInteractionFlags(Qt.NoTextInteraction)
        self._meta_label = QLabel()
        self._meta_label.setObjectName("quickCmdPreviewMeta")
        self._meta_label.setWordWrap(True)
        self._meta_label.setTextFormat(Qt.PlainText)
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(7)
        header_layout.addWidget(self._badge_label, 0, Qt.AlignVCenter)
        header_layout.addWidget(self._title_label, 1, Qt.AlignVCenter)
        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(6)
        card_layout.addLayout(header_layout)
        card_layout.addWidget(self._content_label)
        card_layout.addWidget(self._meta_label)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(0)
        layout.addWidget(self._card)
        shadow_style = quick_preview_popup_shadow()
        shadow = QGraphicsDropShadowEffect(self._card)
        shadow.setBlurRadius(shadow_style["blur_radius"])
        shadow.setOffset(shadow_style["offset_x"], shadow_style["offset_y"])
        shadow.setColor(QColor(*shadow_style["color"]))
        self._card.setGraphicsEffect(shadow)
        self.setStyleSheet(quick_preview_popup_style())

    def set_preview_data(self, name: str, content: str, send_type: str, encoding: str, line_ending: str):
        display_name = str(name or "Untitled")
        display_content = str(content or "")
        display_type = str(send_type or "text")
        display_encoding = str(encoding or "ascii")
        display_line_ending = repr(line_ending or "")
        if len(display_content) > 360:
            display_content = f"{display_content[:360]}..."
        self._title_label.setText(display_name)
        self._content_label.setText(display_content if display_content else " ")
        self._meta_label.setText(
            f"Type: {display_type}   Encoding: {display_encoding}   Line: {display_line_ending}"
        )
        self.setFixedWidth(368)
        self.adjustSize()


class _QuickCmdButton(QPushButton):
    """支持右键菜单 + 拖拽排序的快捷指令按钮。

    - 左键短按 → 触发 ``clicked``（发送指令，逻辑在宿主信号槽里）；
    - 左键拖动超过阈值 → 启动 ``QDrag``，mime 携带源索引；
    - 右键 → 通过 ``Qt.CustomContextMenu`` 上抛给宿主弹出 Edit / Delete 菜单。

    数据流：源索引由宿主在创建按钮时通过 ``set_command_index`` 注入。
    """

    _MIME_TYPE = "application/x-kklab-quickcmd"

    move_requested = Signal(int, int)
    edit_requested = Signal(int)
    delete_requested = Signal(int)

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setAcceptDrops(False)  # 容器统一接收 drop，按钮自身不参与
        self._press_pos = None
        self._cmd_index = -1
        self._dragging = False
        self._preview_data = None
        self._preview_popup = _QuickCmdPreviewPopup()
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(80)
        self._preview_timer.timeout.connect(self._show_preview)
        self._build_action_overlay()
        self._hide_actions_timer = QTimer(self)
        self._hide_actions_timer.setSingleShot(True)
        self._hide_actions_timer.setInterval(60)
        self._hide_actions_timer.timeout.connect(self._maybe_hide_actions)

    def _build_action_overlay(self):
        # 悬浮操作条：用独立的无边框顶层窗口承载，溢出在按钮顶部（参考 -top-2.5）。
        # 不能作为按钮或网格容器的子控件——前者会被裁剪、后者会被 QScrollArea
        # 视口边界裁掉，因此顶层窗口才能真正浮在按钮上边缘之上。
        # 顶层窗口本身保持透明，真正带"整体外边框"的胶囊是其内部子控件，
        # 这样 QSS 的 border/background 才能在半透明顶层窗口上稳定渲染。
        self._action_bar = QFrame(None)
        self._action_bar.setWindowFlags(
            Qt.Tool | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint
        )
        self._action_bar.setAttribute(Qt.WA_TranslucentBackground, True)
        self._action_bar.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self._action_bar.setStyleSheet("QFrame { background: transparent; border: none; }")
        self._action_bar.setCursor(Qt.ArrowCursor)
        self._action_bar.setAttribute(Qt.WA_Hover, True)
        self._action_bar.installEventFilter(self)
        outer_lay = QHBoxLayout(self._action_bar)
        outer_lay.setContentsMargins(2, 2, 2, 2)
        outer_lay.setSpacing(0)
        self._action_pill = QFrame(self._action_bar)
        self._action_pill.setObjectName("quickCmdActionBar")
        self._action_pill.setStyleSheet(quick_action_overlay_container_style())
        outer_lay.addWidget(self._action_pill)
        bar_lay = QHBoxLayout(self._action_pill)
        bar_lay.setContentsMargins(5, 4, 5, 4)
        bar_lay.setSpacing(2)
        self._action_left = self._make_action_btn(
            os.path.join(_SVG_SERIAL_DIR, "chevron-left.svg"), _CLR_TEXT_MUTED, "Move Left"
        )
        self._action_right = self._make_action_btn(
            os.path.join(_SVG_SERIAL_DIR, "chevron-right.svg"), _CLR_TEXT_MUTED, "Move Right"
        )
        self._action_edit = self._make_action_btn(
            os.path.join(_SVG_SERIAL_DIR, "edit.svg"), _CLR_SEND_BG, "Edit macro"
        )
        self._action_delete = self._make_action_btn(
            os.path.join(_SVG_LOGS_DIR, "trash.svg"), _CLR_ERROR, "Delete macro"
        )
        self._action_btns = [
            self._action_left,
            self._action_right,
            self._action_edit,
            self._action_delete,
        ]
        for b in self._action_btns:
            bar_lay.addWidget(b)
        self._action_bar.hide()
        self._action_left.clicked.connect(
            lambda: self.move_requested.emit(self._cmd_index, -1)
        )
        self._action_right.clicked.connect(
            lambda: self.move_requested.emit(self._cmd_index, 1)
        )
        self._action_edit.clicked.connect(
            lambda: self.edit_requested.emit(self._cmd_index)
        )
        self._action_delete.clicked.connect(
            lambda: self.delete_requested.emit(self._cmd_index)
        )

    def _make_action_btn(self, svg_path, color, tip):
        btn = QToolButton(self._action_pill)
        btn.setObjectName("quickCmdAction")
        btn.setStyleSheet(quick_action_overlay_style())
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setFixedSize(18, 18)
        btn.setIconSize(QSize(12, 12))
        btn.setToolTip(tip)
        icon = _tinted_svg_icon(svg_path, color, 12)
        if not icon.isNull():
            btn.setIcon(icon)
        return btn

    def set_move_bounds(self, can_left: bool, can_right: bool):
        self._action_left.setEnabled(can_left)
        self._action_right.setEnabled(can_right)

    def _position_action_bar(self):
        bar = getattr(self, "_action_bar", None)
        if bar is None:
            return
        bar.adjustSize()
        bar_w = bar.sizeHint().width()
        bar_h = bar.sizeHint().height()
        # 顶层窗口用全局坐标定位：右侧与按钮右边缘对齐，整体向上溢出按钮顶部
        # （参考 -top-2.5：操作条底部压在按钮上边缘上方约一半处）。
        top_right = self.mapToGlobal(QPoint(self.width(), 0))
        x = top_right.x() - bar_w - 4
        y = top_right.y() - bar_h + bar_h // 2
        bar.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, "_action_bar", None) is not None and self._action_bar.isVisible():
            self._position_action_bar()

    def _set_actions_visible(self, visible: bool):
        bar = getattr(self, "_action_bar", None)
        if bar is None:
            return
        if visible:
            self._hide_actions_timer.stop()
            self._position_action_bar()
            bar.raise_()
            bar.show()
        else:
            bar.hide()

    def _cleanup_action_bar(self):
        bar = getattr(self, "_action_bar", None)
        if bar is None:
            return
        bar.hide()
        bar.removeEventFilter(self)
        bar.setParent(None)
        bar.deleteLater()
        self._action_bar = None

    def _maybe_hide_actions(self):
        bar = getattr(self, "_action_bar", None)
        if bar is None:
            return
        if self.underMouse() or bar.underMouse():
            return
        bar.hide()

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent  # 局部引入，避免顶部冗余导入
        if obj is getattr(self, "_action_bar", None):
            if event.type() == QEvent.Enter:
                self._hide_actions_timer.stop()
            elif event.type() == QEvent.Leave:
                self._hide_actions_timer.start()
        return super().eventFilter(obj, event)

    def set_command_index(self, idx: int):
        self._cmd_index = idx

    def command_index(self) -> int:
        return self._cmd_index

    def set_preview_data(self, name: str, content: str, send_type: str, encoding: str, line_ending: str):
        self._preview_data = {
            "name": name,
            "content": content,
            "send_type": send_type,
            "encoding": encoding,
            "line_ending": line_ending,
        }

    def enterEvent(self, event):
        super().enterEvent(event)
        self._set_actions_visible(True)
        self._preview_timer.start()

    def leaveEvent(self, event):
        self._preview_timer.stop()
        self._preview_popup.hide()
        self._hide_actions_timer.start()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        self._preview_popup.hide()
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.LeftButton
            and self._press_pos is not None
            and not self._dragging
            and self._cmd_index >= 0
        ):
            if (
                event.position().toPoint() - self._press_pos
            ).manhattanLength() >= QApplication.startDragDistance():
                self._preview_timer.stop()
                self._preview_popup.hide()
                self._dragging = True
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def _show_preview(self):
        if not self._preview_data or self._dragging or not self.underMouse():
            return
        self._preview_popup.set_preview_data(**self._preview_data)
        self._preview_popup.ensurePolished()
        pos = self._bounded_preview_pos()
        self._preview_popup.move(pos)
        self._preview_popup.show()

    def _bounded_preview_pos(self) -> QPoint:
        pos = self.mapToGlobal(QPoint(0, self.height() + 8))
        popup_size = self._preview_popup.sizeHint()
        screen = QApplication.screenAt(pos) or self.screen() or QApplication.primaryScreen()
        if screen is None:
            return pos
        available = screen.availableGeometry()
        safe_margin = 24
        x = min(
            max(pos.x(), available.left() + safe_margin),
            available.right() - popup_size.width() - safe_margin,
        )
        y = pos.y()
        if y + popup_size.height() + safe_margin > available.bottom():
            y = self.mapToGlobal(QPoint(0, -popup_size.height() - 8)).y()
        y = min(
            max(y, available.top() + safe_margin),
            available.bottom() - popup_size.height() - safe_margin,
        )
        return QPoint(x, y)

    def mouseReleaseEvent(self, event):
        # 拖拽中按下释放不触发 click（Qt 会自动把 release 派发给 drop 目标）
        was_dragging = self._dragging
        self._press_pos = None
        self._dragging = False
        if was_dragging:
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _start_drag(self):
        from PySide6.QtGui import QDrag  # 局部引入
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self._MIME_TYPE, str(self._cmd_index).encode())
        drag.setMimeData(mime)
        pixmap = self.grab()
        if not pixmap.isNull():
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec(Qt.MoveAction)
        # 拖拽的 release 派发给 drop 目标，源按钮收不到 mouseReleaseEvent，此处复位拖拽态
        self._dragging = False
        self._press_pos = None


class _ProjectTabBar(QTabBar):
    """支持右键菜单 + 项目 Tab 拖拽排序的 QTabBar 子类。

    - 拖拽：按下左键 + 移动超过阈值则启动；放下时计算源 / 目标 index 并通过
      ``project_reorder_requested(source, target)`` 发射给宿主，由宿主修改
      数据模型后重建 Tab。
    - 拖拽时排除末尾的 "+" 加号 tab（最后一项）。
    - 右键菜单：通过 ``Qt.CustomContextMenu`` 上抛给宿主统一处理。
    """

    project_reorder_requested = Signal(int, int)
    _MIME_TYPE = "application/x-kklab-project-tab"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMovable(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self._press_pos = None
        self._press_index = -1

    def _is_real_tab(self, index: int) -> bool:
        # 约定：最后一个 tab 为 "+" 加号，不参与拖拽
        return 0 <= index < self.count() - 1

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            idx = self.tabAt(event.position().toPoint())
            if self._is_real_tab(idx):
                self._press_pos = event.position().toPoint()
                self._press_index = idx
            else:
                self._press_pos = None
                self._press_index = -1
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            event.buttons() & Qt.LeftButton
            and self._press_pos is not None
            and self._press_index >= 0
        ):
            if (
                event.position().toPoint() - self._press_pos
            ).manhattanLength() >= QApplication.startDragDistance():
                self._start_drag(self._press_index)
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_pos = None
        self._press_index = -1
        super().mouseReleaseEvent(event)

    def _start_drag(self, source_index: int):
        from PySide6.QtGui import QDrag  # 局部引入，避免顶部模块持有未用符号
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self._MIME_TYPE, str(source_index).encode())
        drag.setMimeData(mime)
        rect = self.tabRect(source_index)
        if not rect.isEmpty():
            pixmap = self.grab(rect)
            drag.setPixmap(pixmap)
            drag.setHotSpot(QPoint(rect.width() // 2, rect.height() // 2))
        drag.exec(Qt.MoveAction)
        self._press_pos = None
        self._press_index = -1

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self._MIME_TYPE):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(self._MIME_TYPE):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if not event.mimeData().hasFormat(self._MIME_TYPE):
            return
        try:
            source_index = int(
                bytes(event.mimeData().data(self._MIME_TYPE)).decode()
            )
        except (ValueError, UnicodeDecodeError):
            return
        target_index = self.tabAt(event.position().toPoint())
        # 拖到 "+" tab 或外部 → 视为挪到末尾真实项目
        last_real = self.count() - 2
        if not self._is_real_tab(target_index):
            target_index = last_real if last_real >= 0 else 0
        if source_index == target_index:
            return
        event.acceptProposedAction()
        self.project_reorder_requested.emit(source_index, target_index)


class _QuickCommandPickerPopup(QFrame):
    _ENTRY_ROLE = Qt.UserRole + 1
    _KEY_ROLE = Qt.UserRole + 2

    def __init__(self, parent=None, quick_commands=None, on_pick=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("pkPopup")
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setStyleSheet(self._picker_style())
        self._entries = list(quick_commands or [])
        self._on_pick = on_pick
        self.setFixedWidth(540)

        self._tree_data = {}
        self._order = []
        for entry in self._entries:
            project = entry.get("project") or "未分组项目"
            group = entry.get("group") or "默认分组"
            if project not in self._tree_data:
                self._tree_data[project] = {}
                self._order.append(project)
            self._tree_data[project].setdefault(group, []).append(entry)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        self._search = QLineEdit()
        self._search.setObjectName("pkSearch")
        self._search.setPlaceholderText("搜索指令 / 分组 / 项目…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._apply_filter)
        self._search.returnPressed.connect(self._activate_current)
        root.addWidget(self._search)

        cols = QHBoxLayout()
        cols.setContentsMargins(0, 0, 0, 0)
        cols.setSpacing(6)

        self._proj_list = self._make_column("pkColProject")
        self._group_list = self._make_column("pkColGroup")
        self._cmd_list = self._make_column("pkColCmd")
        cols.addWidget(self._proj_list, 1)
        cols.addWidget(self._group_list, 1)
        cols.addWidget(self._cmd_list, 1)
        root.addLayout(cols, 1)

        self._search_list = QListWidget()
        self._search_list.setObjectName("pkSearchList")
        self._search_list.setMouseTracking(True)
        self._search_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._search_list.setMaximumHeight(320)
        self._search_list.setMinimumHeight(220)
        self._search_list.itemClicked.connect(self._on_search_clicked)
        self._search_list.hide()
        root.addWidget(self._search_list, 1)

        self._proj_list.itemEntered.connect(self._on_project_changed)
        self._proj_list.currentItemChanged.connect(
            lambda cur, _prev: self._on_project_changed(cur)
        )
        self._group_list.itemEntered.connect(self._on_group_changed)
        self._group_list.currentItemChanged.connect(
            lambda cur, _prev: self._on_group_changed(cur)
        )
        self._cmd_list.itemClicked.connect(self._on_cmd_clicked)

        self._build_projects()

    def _make_column(self, name):
        lst = QListWidget()
        lst.setObjectName(name)
        lst.setMouseTracking(True)
        lst.setEditTriggers(QAbstractItemView.NoEditTriggers)
        lst.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        lst.setMaximumHeight(320)
        lst.setMinimumHeight(220)
        return lst

    def popup_at(self, anchor):
        self.adjustSize()
        screen = self.screen() or QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else None
        if anchor is not None:
            below = anchor.mapToGlobal(QPoint(0, anchor.height() + 4))
            pos = below
            if avail is not None:
                if pos.x() + self.width() > avail.right():
                    pos.setX(avail.right() - self.width())
                if pos.x() < avail.left():
                    pos.setX(avail.left())
                if pos.y() + self.height() > avail.bottom():
                    above = anchor.mapToGlobal(QPoint(0, -self.height() - 4))
                    pos = above
            self.move(pos)
        else:
            self.move(QCursor.pos())
        self.show()
        self._search.setFocus()

    def _picker_style(self) -> str:
        return f"""
            QFrame#pkPopup {{
                background-color: {_CLR_BG_CARD};
                border: 1px solid {_CLR_BORDER_HOVER};
                border-radius: 12px;
            }}
            QLineEdit#pkSearch {{
                background-color: {_CLR_INPUT_BG};
                border: 1px solid {_CLR_BORDER};
                border-radius: 8px;
                color: {_CLR_TEXT_BTN_LOG};
                font-size: 12px; font-family: {_UI_FONT};
                padding: 6px 9px;
                min-height: 22px;
            }}
            QLineEdit#pkSearch:focus {{ border: 1px solid {_CLR_FILTER_BORDER}; }}
            QListWidget#pkColProject, QListWidget#pkColGroup,
            QListWidget#pkColCmd, QListWidget#pkSearchList {{
                background-color: {_CLR_INPUT_BG};
                border: 1px solid {_CLR_BORDER};
                border-radius: 10px;
                color: {_CLR_TEXT_BTN_LOG};
                font-size: 12px; font-family: {_UI_FONT};
                outline: none;
                padding: 4px;
            }}
            QListWidget#pkColProject::item, QListWidget#pkColGroup::item,
            QListWidget#pkColCmd::item, QListWidget#pkSearchList::item {{
                min-height: 25px;
                padding: 3px 6px;
                border-radius: 6px;
            }}
            QListWidget#pkColProject::item:hover, QListWidget#pkColGroup::item:hover,
            QListWidget#pkColCmd::item:hover, QListWidget#pkSearchList::item:hover {{
                background-color: {_CLR_BORDER};
            }}
            QListWidget#pkColProject::item:selected, QListWidget#pkColGroup::item:selected,
            QListWidget#pkColCmd::item:selected, QListWidget#pkSearchList::item:selected {{
                background-color: {_CLR_SELECTION_BG};
                color: {_CLR_TEXT_TITLE};
            }}
        """

    def _build_projects(self):
        title_font = QFont(self._proj_list.font())
        title_font.setBold(True)
        self._proj_list.clear()
        for project in self._order:
            item = QListWidgetItem(f"{project}  ›")
            item.setData(self._KEY_ROLE, project)
            item.setFont(title_font)
            item.setForeground(QColor(_CLR_TEXT_TITLE))
            self._proj_list.addItem(item)
        self._group_list.clear()
        self._cmd_list.clear()
        if self._proj_list.count() == 1:
            self._on_project_changed(self._proj_list.item(0))

    def _on_project_changed(self, item):
        self._group_list.clear()
        self._cmd_list.clear()
        if item is None:
            return
        project = item.data(self._KEY_ROLE)
        if project is None:
            return
        groups = self._tree_data.get(project, {})
        for group in groups:
            g_item = QListWidgetItem(f"{group}  ›")
            g_item.setData(self._KEY_ROLE, (project, group))
            g_item.setForeground(QColor(_CLR_TEXT_MUTED))
            self._group_list.addItem(g_item)
        if self._group_list.count() == 1:
            self._on_group_changed(self._group_list.item(0))

    def _on_group_changed(self, item):
        self._cmd_list.clear()
        if item is None:
            return
        key = item.data(self._KEY_ROLE)
        if not key:
            return
        project, group = key
        for entry in self._tree_data.get(project, {}).get(group, []):
            label = entry.get("name", "") or entry.get("content", "")
            c_item = QListWidgetItem(label)
            c_item.setData(self._ENTRY_ROLE, entry)
            c_item.setToolTip(entry.get("content", ""))
            self._cmd_list.addItem(c_item)

    def _on_cmd_clicked(self, item):
        if item is None:
            return
        entry = item.data(self._ENTRY_ROLE)
        if not entry:
            return
        if callable(self._on_pick):
            self._on_pick(entry)
        self.close()

    def _apply_filter(self, text):
        needle = (text or "").strip().lower()
        if not needle:
            self._search_list.hide()
            self._proj_list.show()
            self._group_list.show()
            self._cmd_list.show()
            return
        self._proj_list.hide()
        self._group_list.hide()
        self._cmd_list.hide()
        self._search_list.show()
        self._search_list.clear()
        for entry in self._entries:
            haystack = " ".join(str(entry.get(k, "")) for k in
                                 ("name", "content", "group", "project")).lower()
            if needle not in haystack:
                continue
            project = entry.get("project") or "未分组项目"
            group = entry.get("group") or "默认分组"
            name = entry.get("name", "") or entry.get("content", "")
            item = QListWidgetItem(f"{project} / {group} / {name}")
            item.setData(self._ENTRY_ROLE, entry)
            item.setToolTip(entry.get("content", ""))
            self._search_list.addItem(item)
        if self._search_list.count() > 0:
            self._search_list.setCurrentRow(0)

    def _on_search_clicked(self, item):
        self._on_cmd_clicked(item)

    def _activate_current(self):
        if self._search_list.isVisible():
            item = self._search_list.currentItem() or (
                self._search_list.item(0) if self._search_list.count() else None
            )
            if item is not None:
                self._on_cmd_clicked(item)
            return
        item = self._cmd_list.currentItem()
        if item is None and self._cmd_list.count() > 0:
            item = self._cmd_list.item(0)
        if item is not None:
            self._on_cmd_clicked(item)
