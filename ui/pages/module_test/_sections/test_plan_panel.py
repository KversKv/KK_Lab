"""TestPlanPanel — 测试项面板（工具行 + TestPlanView + 委托）。

- 工具行：搜索框 / 全选(切换) / 仅失败(切换) / 已选计数；
- 视图：``QTreeView`` + ``TestPlanModel`` + ``QSortFilterProxyModel``（名称过滤、
  仅失败过滤），分组默认展开；
- 委托：``_StatusBadgeDelegate``（状态徽章着色 + running 呼吸点）、
  ``_ParamDelegate``（⚙ + 「已改」标记，点击列发 ``paramsRequested``）；
- 键盘：空格切换勾选、Enter 打开参数、Ctrl+A 全选/取消全选。

运行状态着色完全由 Model StatusRole 驱动（不再逐项 setForeground），
从根源上消除"全局 QSS 盖掉 ForegroundRole"的旧坑。
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import QModelIndex, QSize, QSortFilterProxyModel, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QHeaderView, QLineEdit,
    QPushButton, QStyledItemDelegate, QTreeView, QVBoxLayout, QWidget,
)

import os

from ui.models.test_plan_model import (
    COL_CHECK, COL_DURATION, COL_INSTRUMENT, COL_NAME, COL_PARAMS, COL_RESULT,
    COL_STATUS, CustomizedRole, HasParamsRole, IsGroupRole, KeyRole,
    ST_FAIL, ST_IDLE, ST_NA, ST_PASS, ST_RUNNING, ST_SCOPE_MISSING,
    ST_UNSELECTED, ST_WAITING, StatusRole, TestPlanModel,
)
from ui.resource_path import get_resource_base
from ui.theme import current_theme, dp, refresh_style
from ui.theme.tokens import module_dark_tokens
from ui.utils.icon_utils import tinted_svg_icon
from ui.widgets.badge_delegate import draw_pill_badge, paint_item_background

_PARAM_ICON = os.path.join(get_resource_base(), "resources", "icons", "settings.svg")
_SEARCH_ICON = os.path.join(get_resource_base(), "resources", "icons", "search.svg")


# ---------------------------------------------------------------------- 过滤代理
class _PlanFilterProxy(QSortFilterProxyModel):
    """名称子串过滤 + 仅失败过滤；分组行任一子行可见则可见。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._needle = ""
        self._only_failed = False

    def set_needle(self, text: str) -> None:
        self._needle = (text or "").strip().lower()
        self.invalidateFilter()

    def set_only_failed(self, on: bool) -> None:
        self._only_failed = on
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        model: TestPlanModel = self.sourceModel()
        idx = model.index(source_row, 0, source_parent)
        if idx.data(IsGroupRole):
            return any(self.filterAcceptsRow(r, idx)
                       for r in range(model.rowCount(idx)))
        if self._only_failed and idx.data(StatusRole) != ST_FAIL:
            return False
        if self._needle:
            name = str(model.index(source_row, COL_NAME, source_parent).data(Qt.DisplayRole) or "")
            if self._needle not in name.lower():
                return False
        return True


# ---------------------------------------------------------------------- 状态徽章委托
class _StatusBadgeDelegate(QStyledItemDelegate):
    """Status 列徽章：圆角底 + 状态色文字；running 附呼吸点（panel 定时器驱动）。"""

    _STATE_ATTR = {
        ST_IDLE: "state_skipped",
        ST_WAITING: "state_warning",
        ST_RUNNING: "state_running",
        ST_PASS: "state_success",
        ST_FAIL: "state_error",
        ST_NA: "state_info",
        ST_UNSELECTED: "state_skipped",
        ST_SCOPE_MISSING: "state_warning",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pulse = False  # 呼吸点开关（由 panel QTimer 翻转）

    def paint(self, painter: QPainter, option, index) -> None:
        if index.column() != COL_STATUS or index.data(IsGroupRole):
            super().paint(painter, option, index)
            return
        status = index.data(StatusRole) or ST_IDLE
        text = index.data(Qt.DisplayRole) or ""
        # Module Test 专属 token（与全局 dark_tokens 解耦，本页用对新色板）
        theme = module_dark_tokens()
        state = getattr(theme, self._STATE_ATTR.get(status, "state_skipped"))

        # 先由 QStyle 绘制选中/hover 背景（与其它列一致），再叠加徽章
        paint_item_background(painter, option)
        draw_pill_badge(painter, option.rect, text, state,
                        pulse=status == ST_RUNNING and self.pulse)


class _ParamDelegate(QStyledItemDelegate):
    """Params 列：绘制 ⚙（已 override 高亮着色）；无可配参数显示 —。"""

    def paint(self, painter: QPainter, option, index) -> None:
        if index.column() != COL_PARAMS or index.data(IsGroupRole):
            super().paint(painter, option, index)
            return
        theme = current_theme()
        # 先由 QStyle 绘制选中/hover 背景（与其它列一致），再叠加齿轮图标
        paint_item_background(painter, option)
        painter.save()
        if not index.data(HasParamsRole):
            painter.setPen(QColor(theme.text_disabled))
            painter.drawText(option.rect, Qt.AlignCenter, "—")
        else:
            customized = bool(index.data(CustomizedRole))
            color = theme.state_info.fg if customized else theme.text_muted
            rect = option.rect
            side = min(rect.height() - 6, 16)
            icon_rect = rect.adjusted(0, 0, 0, 0)
            icon_rect.setSize(QSize(side, side))
            icon_rect.moveCenter(rect.center())
            tinted_svg_icon(_PARAM_ICON, color, side).paint(painter, icon_rect)
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        """列宽固定仅容纳齿轮图标，避免 ResizeToContents 过窄。"""
        if index.column() != COL_PARAMS or index.data(IsGroupRole):
            return super().sizeHint(option, index)
        # 图标 16px + 左右各 8px padding = 32px；高度钳到 34（同 $table_row_h），
        # 配合 setUniformRowHeights 使 hover 重算 sizeHint 不再把行撑高溢出
        return QSize(32, dp(34))


# ---------------------------------------------------------------------- 视图
class TestPlanView(QTreeView):
    """测试项树视图（键盘：空格勾选 / Enter 参数 / Ctrl+A 全选）。"""

    paramsRequested = Signal(str)
    selectAllRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

    def keyPressEvent(self, event) -> None:
        key = event.key()
        mods = event.modifiers()
        if key == Qt.Key_Space:
            self._toggle_current()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            self._emit_params_for_current()
            return
        if key == Qt.Key_A and mods & Qt.ControlModifier:
            self.selectAllRequested.emit()
            return
        super().keyPressEvent(event)

    def _toggle_current(self) -> None:
        proxy_index = self.currentIndex()
        if not proxy_index.isValid():
            return
        proxy = self.model()
        if not isinstance(proxy, _PlanFilterProxy):
            return
        src = proxy.mapToSource(proxy_index).siblingAtColumn(COL_CHECK)
        state = src.data(Qt.CheckStateRole)
        target = Qt.Unchecked if state == Qt.Checked else Qt.Checked
        proxy.sourceModel().setData(src, target, Qt.CheckStateRole)

    def _emit_params_for_current(self) -> None:
        index = self.currentIndex()
        if not index.isValid():
            return
        key = index.data(KeyRole)
        if key:
            self.paramsRequested.emit(key)


# ---------------------------------------------------------------------- 面板
class TestPlanPanel(QWidget):
    """测试项面板（工具行 + 树视图）。"""

    paramsRequested = Signal(str)   # item_key
    selectionChanged = Signal()

    def __init__(self, registry: Mapping, standalone: Sequence[str] = (),
                 parent: QWidget | None = None):
        super().__init__(parent)
        # table.qss 专用段：面板内表格去自身边框透底（外层容器/相邻卡片已提供外框，
        # 避免表格边框与其重叠），内容留白由 margins 提供
        self.setObjectName("testPlanPanel")
        self._model = TestPlanModel(registry, standalone, self)
        self._proxy = _PlanFilterProxy(self)
        self._proxy.setSourceModel(self._model)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)

        # —— 工具行 ——
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        bar.setSpacing(6)
        self.search_edit = QLineEdit()
        self.search_edit.setObjectName("searchEdit")
        self.search_edit.setPlaceholderText("搜索测试项…（Ctrl+F）")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setMaximumWidth(240)
        # 左侧内嵌放大镜图标（纯视觉，占位由 QSS #searchEdit padding-left 提供）
        _muted = current_theme().text_muted
        self.search_edit.addAction(tinted_svg_icon(_SEARCH_ICON, _muted, 14),
                                   QLineEdit.LeadingPosition)
        self.search_edit.textChanged.connect(self._proxy.set_needle)
        bar.addWidget(self.search_edit)

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.setProperty("variant", "ghost")
        self.select_all_btn.setToolTip("全选/取消全选「自动测试序列」（Ctrl+A）")
        self.select_all_btn.clicked.connect(self.toggle_all)
        bar.addWidget(self.select_all_btn)

        self.only_failed_btn = QPushButton("仅失败")
        self.only_failed_btn.setProperty("variant", "ghost")
        self.only_failed_btn.setCheckable(True)
        self.only_failed_btn.toggled.connect(self._proxy.set_only_failed)
        bar.addWidget(self.only_failed_btn)

        bar.addStretch()
        self._stats_label = self._make_stats_label()
        bar.addWidget(self._stats_label)
        root.addLayout(bar)

        # —— 视图 ——
        self.view = TestPlanView(self)
        self.view.setModel(self._proxy)
        self.view.setItemDelegateForColumn(COL_STATUS, _StatusBadgeDelegate(self.view))
        self.view.setItemDelegateForColumn(COL_PARAMS, _ParamDelegate(self.view))
        header = self.view.header()
        header.setSectionResizeMode(COL_CHECK, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(COL_NAME, QHeaderView.Stretch)
        for col in (COL_INSTRUMENT, COL_STATUS, COL_RESULT, COL_DURATION, COL_PARAMS):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        # 末列（COL_PARAMS）默认被 stretchLastSection 拉伸填满右侧，导致整列宽度过大、
        # 任意位置点击都触发参数弹窗；关闭后由 COL_NAME(Stretch) 独占剩余空间，参数列按
        # _ParamDelegate.sizeHint() 收窄为仅容齿轮图标。
        header.setStretchLastSection(False)
        self.view.expandAll()

        self.view.paramsRequested.connect(self.paramsRequested)
        self.view.selectAllRequested.connect(self.toggle_all)
        self.view.clicked.connect(self._on_clicked)
        self._model.dataChanged.connect(self._on_model_data_changed)
        root.addWidget(self.view, 1)

        # running 呼吸点定时器
        self._pulse_timer = QTimer(self)
        self._pulse_timer.setInterval(500)
        self._pulse_timer.timeout.connect(self._on_pulse)

        self._refresh_stats()

    @staticmethod
    def _make_stats_label():
        from PySide6.QtWidgets import QLabel
        lbl = QLabel()
        lbl.setObjectName("statsBadge")
        return lbl

    # ------------------------------------------------------------------ 内部
    def _on_clicked(self, proxy_index) -> None:
        if proxy_index.column() == COL_PARAMS:
            key = proxy_index.data(KeyRole)
            if key and self._model.has_params(key):
                self.paramsRequested.emit(key)

    def _on_model_data_changed(self, *_args) -> None:
        self._refresh_stats()
        self.selectionChanged.emit()

    def _on_pulse(self) -> None:
        delegate = self.view.itemDelegateForColumn(COL_STATUS)
        if isinstance(delegate, _StatusBadgeDelegate):
            delegate.pulse = not delegate.pulse
            self.view.viewport().update()

    def _refresh_stats(self) -> None:
        checked, total = self._model.stats()
        self._stats_label.setText(f"已选 {checked}/{total}")
        # 选中数 > 0 时徽章转主色（纯视觉属性，QSS #statsBadge[hasSelection]）
        self._stats_label.setProperty("hasSelection", "true" if checked > 0 else "false")
        refresh_style(self._stats_label)
        self.select_all_btn.setText(
            "取消全选" if self._model.auto_all_checked() else "全选")

    # ------------------------------------------------------------------ 对外 API（子页基类调用）
    def selected_keys(self) -> list[str]:
        return self._model.selected_keys()

    def set_checked_keys(self, keys) -> None:
        self._model.set_checked_keys(keys)
        self.view.expandAll()

    def toggle_all(self) -> None:
        self._model.toggle_all_auto()

    def set_scope_connected(self, connected: bool) -> None:
        self._model.set_scope_connected(connected)

    def enter_run_state(self, selected_keys) -> None:
        self._model.enter_run_state(selected_keys)
        self.view.expandAll()
        self._pulse_timer.start()

    def exit_run_state(self) -> None:
        self._pulse_timer.stop()
        self._model.exit_run_state()
        self.view.expandAll()

    def mark_item_running(self, item_key: str) -> None:
        self._model.mark_item_running(item_key)

    def mark_item_done(self, item_key: str, verdict: str) -> None:
        self._model.mark_item_done(item_key, verdict)

    def set_item_duration(self, item_key: str, seconds) -> None:
        self._model.set_item_duration(item_key, seconds)

    def set_item_customized(self, item_key: str, customized: bool) -> None:
        self._model.set_item_customized(item_key, customized)

    def is_running_locked(self) -> bool:
        return self._model.is_running_locked()

    def focus_search(self) -> None:
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def model(self) -> TestPlanModel:
        return self._model


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "..", "..")))

    from PySide6.QtWidgets import QApplication

    from ui.theme import apply_qss

    def _fake_run(ctx):
        return {}

    registry = {
        "ldo_line_reg": ("Line Regulation", _fake_run, False, True, []),
        "ldo_load_transient": ("Load Transient", _fake_run, True, True, [1]),
        "ldo_quiescent": ("Quiescent Current", _fake_run, False, True, []),
        "ldo_psrr": ("PSRR", _fake_run, True, False, []),
    }
    app = QApplication(sys.argv)
    panel = TestPlanPanel(registry, standalone=("ldo_psrr",))
    apply_qss(panel, "controls")
    apply_qss(panel, "table")
    panel.paramsRequested.connect(lambda k: print("params:", k))
    panel.setWindowTitle("TestPlanPanel Demo")
    panel.resize(760, 420)
    panel.show()
    sys.exit(app.exec())
