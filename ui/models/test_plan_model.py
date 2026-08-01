"""TestPlanModel — 测试项树模型（自动测试序列 / 单项测试 两分组）。

数据来源：``ITEMS_REGISTRY``（``key -> (name, run_fn, needs_scope, checked, params)``）
+ ``STANDALONE_ITEMS``。模型只读注册表元数据（name/needs_scope/checked/params），
不 import core（由调用方把注册表 dict 传入），保持 ui 层单向依赖。

列（7）：
    0 Enabled(勾选)  1 Name  2 Instrument  3 Status(徽章)  4 Result(摘要)
    5 Duration  6 Params(⚙)

运行状态着色（替代旧"逐项 setForeground + QSS 盖色 hack"）：
状态存 Model（``StatusRole``），由 StatusDelegate 绘制徽章；
勾选锁定走 ``flags()``（运行期移除 ``ItemIsUserCheckable``）。
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from PySide6.QtCore import QAbstractItemModel, QModelIndex, Qt
from PySide6.QtGui import QBrush, QColor

from ui.theme import current_theme

# —— 列 ——
COL_CHECK = 0
COL_NAME = 1
COL_INSTRUMENT = 2
COL_STATUS = 3
COL_RESULT = 4
COL_DURATION = 5
COL_PARAMS = 6
COL_COUNT = 7

# —— 角色 ——
KeyRole = Qt.UserRole + 1            # item_key（分组行返回 None）
IsGroupRole = Qt.UserRole + 2
NeedsScopeRole = Qt.UserRole + 3
StatusRole = Qt.UserRole + 4         # ST_* 原始状态（委托着色用）
CustomizedRole = Qt.UserRole + 5     # 参数已被 override
HasParamsRole = Qt.UserRole + 6
GroupKeyRole = Qt.UserRole + 7       # "auto" / "standalone"

# —— 状态 ——
ST_IDLE = "idle"                     # 待运行（可勾选）
ST_WAITING = "waiting"               # 本次已选，等待执行
ST_RUNNING = "running"               # 执行中
ST_PASS = "pass"
ST_FAIL = "fail"
ST_NA = "na"                         # 完成但无判定（N/A）
ST_UNSELECTED = "unselected"         # 本次未选
ST_SCOPE_MISSING = "scope_missing"   # 需要示波器但未连接

_STATUS_TEXT = {
    ST_IDLE: "待命",
    ST_WAITING: "等待中",
    ST_RUNNING: "▶ 进行中",
    ST_PASS: "✓ PASS",
    ST_FAIL: "✗ FAIL",
    ST_NA: "✓ 完成",
    ST_UNSELECTED: "未选",
    ST_SCOPE_MISSING: "未接示波器",
}

GROUP_AUTO = "auto"
GROUP_STANDALONE = "standalone"


class _Item:
    __slots__ = ("key", "name", "needs_scope", "has_params", "checked",
                 "status", "result_text", "duration_s", "customized", "group")

    def __init__(self, key: str, name: str, needs_scope: bool, checked: bool,
                 has_params: bool, group: "_Group"):
        self.key = key
        self.name = name
        self.needs_scope = needs_scope
        self.has_params = has_params
        self.checked = checked
        self.status = ST_IDLE
        self.result_text = ""
        self.duration_s: float | None = None
        self.customized = False
        self.group = group


class _Group:
    __slots__ = ("key", "title", "items")

    def __init__(self, key: str, title: str):
        self.key = key
        self.title = title
        self.items: list[_Item] = []


class TestPlanModel(QAbstractItemModel):
    """测试项树模型：根 → 分组（≤2）→ 测试项。"""

    def __init__(self, registry: Mapping, standalone: Sequence[str] = (),
                 parent=None):
        super().__init__(parent)
        self._groups: list[_Group] = []
        self._items: dict[str, _Item] = {}
        self._running = False
        self._scope_connected = True
        self._build(registry, tuple(standalone))

    # ------------------------------------------------------------------ 构建
    def _build(self, registry: Mapping, standalone: tuple[str, ...]) -> None:
        auto_keys = [k for k in registry if k not in standalone]
        stand_keys = [k for k in standalone if k in registry]
        for gkey, title, keys in (
            (GROUP_AUTO, "自动测试序列", auto_keys),
            (GROUP_STANDALONE, "单项测试", stand_keys),
        ):
            if not keys:
                continue
            group = _Group(gkey, title)
            for key in keys:
                name, _fn, needs_scope, checked, params = registry[key]
                item = _Item(key, name, bool(needs_scope), bool(checked),
                             bool(params), group)
                group.items.append(item)
                self._items[key] = item
            self._groups.append(group)
        self._refresh_scope_status()

    # ------------------------------------------------------------------ 结构
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        if not parent.isValid():
            return self.createIndex(row, column, self._groups[row])
        group = parent.internalPointer()
        if isinstance(group, _Group) and row < len(group.items):
            return self.createIndex(row, column, group.items[row])
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:
        if not index.isValid():
            return QModelIndex()
        node = index.internalPointer()
        if isinstance(node, _Item):
            group = node.group
            return self.createIndex(self._groups.index(group), 0, group)
        return QModelIndex()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if not parent.isValid():
            return len(self._groups)
        node = parent.internalPointer()
        return len(node.items) if isinstance(node, _Group) else 0

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return COL_COUNT

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        return ("", "测试项", "主要仪器", "状态", "结果摘要", "耗时", "参数")[section]

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        node = index.internalPointer()
        base = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.column() == COL_CHECK:
            base |= Qt.ItemIsSelectable
            if not self._running:
                base |= Qt.ItemIsUserCheckable
            if isinstance(node, _Group):
                base |= Qt.ItemIsAutoTristate
        return base

    # ------------------------------------------------------------------ 数据
    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        node = index.internalPointer()
        col = index.column()
        # 勾选列内容尺寸提示：保证 checkbox（含分支缩进）完整显示，不被裁切
        if col == COL_CHECK and role == Qt.SizeHintRole:
            from PySide6.QtCore import QSize
            return QSize(28, 24)
        if isinstance(node, _Group):
            return self._group_data(node, col, role)
        return self._item_data(node, col, role)

    def _group_data(self, group: _Group, col: int, role: int):
        if role == IsGroupRole:
            return True
        if role == GroupKeyRole:
            return group.key
        if role == Qt.ForegroundRole and col == COL_NAME:
            return QBrush(QColor(current_theme().text_secondary))
        if col == COL_CHECK and role == Qt.CheckStateRole:
            states = {i.checked for i in group.items}
            if len(states) == 1:
                return Qt.Checked if states.pop() else Qt.Unchecked
            return Qt.PartiallyChecked
        if col == COL_NAME and role == Qt.DisplayRole:
            checked = sum(1 for i in group.items if i.checked)
            return f"{group.title}（{checked}/{len(group.items)}）"
        return None

    def _item_data(self, item: _Item, col: int, role: int):
        if role == IsGroupRole:
            return False
        if role == KeyRole:
            return item.key
        if role == NeedsScopeRole:
            return item.needs_scope
        if role == StatusRole:
            return item.status
        if role == CustomizedRole:
            return item.customized
        if role == HasParamsRole:
            return item.has_params
        if role == Qt.ForegroundRole:
            theme = current_theme()
            if col == COL_NAME:
                return QBrush(QColor(theme.text_primary))
            if col in (COL_INSTRUMENT, COL_RESULT, COL_DURATION):
                return QBrush(QColor(theme.text_secondary))
        if col == COL_CHECK and role == Qt.CheckStateRole:
            return Qt.Checked if item.checked else Qt.Unchecked
        if col == COL_NAME:
            if role == Qt.DisplayRole:
                return item.name
        elif col == COL_INSTRUMENT and role == Qt.DisplayRole:
            return "示波器" if item.needs_scope else "N6705C"
        elif col == COL_STATUS and role == Qt.DisplayRole:
            return _STATUS_TEXT.get(item.status, item.status)
        elif col == COL_RESULT and role == Qt.DisplayRole:
            return item.result_text
        elif col == COL_DURATION and role == Qt.DisplayRole:
            return "" if item.duration_s is None else f"{item.duration_s:.1f}s"
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.EditRole) -> bool:
        if not index.isValid() or index.column() != COL_CHECK or role != Qt.CheckStateRole:
            return False
        if self._running:
            return False
        node = index.internalPointer()
        try:
            checked = Qt.CheckState(value) == Qt.Checked
        except (TypeError, ValueError):
            checked = bool(value)
        if isinstance(node, _Item):
            node.checked = bool(checked)
            self._emit_row_changed(node)
            self._emit_group_changed(node.group)
            return True
        if isinstance(node, _Group):
            for item in node.items:
                item.checked = bool(checked)
            self._emit_group_changed(node, children=True)
            return True
        return False

    # ------------------------------------------------------------------ 变更通知
    def _emit_row_changed(self, item: _Item) -> None:
        group_row = self._groups.index(item.group)
        item_row = item.group.items.index(item)
        idx = self.index(item_row, 0, self.index(group_row, 0))
        self.dataChanged.emit(
            idx.siblingAtColumn(0), idx.siblingAtColumn(COL_COUNT - 1))

    def _emit_group_changed(self, group: _Group, *, children: bool = False) -> None:
        row = self._groups.index(group)
        gidx = self.index(row, 0)
        self.dataChanged.emit(gidx, gidx.siblingAtColumn(COL_COUNT - 1))
        if children and group.items:
            top = self.index(0, 0, gidx)
            bottom = self.index(len(group.items) - 1, COL_COUNT - 1, gidx)
            self.dataChanged.emit(top, bottom)

    def _emit_all_items_changed(self) -> None:
        for group in self._groups:
            self._emit_group_changed(group, children=True)

    # ------------------------------------------------------------------ 勾选 API
    def selected_keys(self) -> list[str]:
        return [k for k, i in self._items.items() if i.checked]

    def set_checked_keys(self, keys: set[str] | list[str]) -> None:
        sel = set(keys)
        for item in self._items.values():
            item.checked = item.key in sel
        self._emit_all_items_changed()

    def toggle_all_auto(self) -> bool:
        """全选/取消全选（仅"自动测试序列"分组，与旧行为一致）。返回新勾选态。"""
        group = next((g for g in self._groups if g.key == GROUP_AUTO), None)
        if group is None:
            return False
        target = not all(i.checked for i in group.items)
        for item in group.items:
            item.checked = target
        self._emit_group_changed(group, children=True)
        return target

    def auto_all_checked(self) -> bool:
        group = next((g for g in self._groups if g.key == GROUP_AUTO), None)
        return bool(group) and all(i.checked for i in group.items)

    def stats(self) -> tuple[int, int]:
        """(已勾选, 总数)。"""
        total = len(self._items)
        return sum(1 for i in self._items.values() if i.checked), total

    def failed_keys(self) -> list[str]:
        return [k for k, i in self._items.items() if i.status == ST_FAIL]

    # ------------------------------------------------------------------ 状态 API
    def set_scope_connected(self, connected: bool) -> None:
        """示波器连接状态联动（运行期不覆盖状态列，与旧守卫一致）。"""
        self._scope_connected = connected
        if self._running:
            return
        self._refresh_scope_status()
        self._emit_all_items_changed()

    def _refresh_scope_status(self) -> None:
        for item in self._items.values():
            if item.needs_scope and not self._scope_connected:
                item.status = ST_SCOPE_MISSING
                item.result_text = "未接示波器"
            elif item.status == ST_SCOPE_MISSING:
                item.status = ST_IDLE
                item.result_text = ""

    def enter_run_state(self, selected_keys: Sequence[str]) -> None:
        """进入运行态：锁定勾选，已选项"等待中"、未选项"未选"。"""
        self._running = True
        sel = set(selected_keys)
        for item in self._items.values():
            item.duration_s = None
            if item.key in sel:
                item.status = ST_WAITING
                item.result_text = ""
            else:
                item.status = ST_UNSELECTED
                item.result_text = ""
        self._emit_all_items_changed()

    def exit_run_state(self) -> None:
        """退出运行态：恢复勾选交互与待命/未接示波器状态。"""
        self._running = False
        for item in self._items.values():
            item.status = ST_IDLE
            item.result_text = ""
        self._refresh_scope_status()
        self._emit_all_items_changed()

    def mark_item_running(self, item_key: str) -> None:
        item = self._items.get(item_key)
        if item is None:
            return
        item.status = ST_RUNNING
        self._emit_row_changed(item)

    def mark_item_done(self, item_key: str, verdict: str) -> None:
        """verdict: ``PASS`` / ``FAIL`` / 其它（N/A，与旧 _mark_item_done 一致）。"""
        item = self._items.get(item_key)
        if item is None:
            return
        v = (verdict or "").upper()
        if v == "PASS":
            item.status = ST_PASS
        elif v == "FAIL":
            item.status = ST_FAIL
        else:
            item.status = ST_NA
        item.result_text = verdict or "N/A"
        self._emit_row_changed(item)

    def set_item_duration(self, item_key: str, seconds: float | None) -> None:
        item = self._items.get(item_key)
        if item is None:
            return
        item.duration_s = seconds
        self._emit_row_changed(item)

    def set_item_result(self, item_key: str, text: str) -> None:
        item = self._items.get(item_key)
        if item is None:
            return
        item.result_text = text
        self._emit_row_changed(item)

    def set_item_customized(self, item_key: str, customized: bool) -> None:
        item = self._items.get(item_key)
        if item is None:
            return
        item.customized = customized
        self._emit_row_changed(item)

    def customized_keys(self) -> list[str]:
        return [k for k, i in self._items.items() if i.customized]

    def has_params(self, item_key: str) -> bool:
        item = self._items.get(item_key)
        return bool(item and item.has_params)

    def is_running_locked(self) -> bool:
        return self._running

    def key_at(self, index: QModelIndex) -> str | None:
        node = index.internalPointer() if index.isValid() else None
        return node.key if isinstance(node, _Item) else None
