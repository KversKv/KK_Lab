#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[兼容层] Module Test 旧控件入口（P3 重构后仅 re-export，P5 删除）。

- ``CollapsibleGroupBox`` → ``ui.widgets.card.Card``
- ``ItemParamsDialog`` → ``ui.pages.module_test.dialogs.item_params_dialog``
- ``GroupsTableEditor``（旧 ``_GroupsEditor``）→ ``ui.widgets.groups_editor``
- ``DIALOG_QSS`` → ``ui.theme.qss/dialog.qss`` 渲染结果（deprecated）

新代码请直接从上述新位置导入。
"""
from __future__ import annotations

import warnings as _warnings

from ui.theme.theme import load_qss
from ui.widgets.card import Card
from ui.widgets.groups_editor import GroupColumn, GroupsTableEditor

from ui.pages.module_test.dialogs.item_params_dialog import ItemParamsDialog


class CollapsibleGroupBox(Card):
    """旧可折叠分组框（兼容别名）：映射到 Card（collapsible=True）。"""

    def __init__(self, title: str, expanded: bool = True, parent=None):
        _warnings.warn(
            "CollapsibleGroupBox 已废弃，请改用 ui.widgets.card.Card",
            DeprecationWarning, stacklevel=2)
        super().__init__(title, collapsible=True, collapsed=not expanded,
                         parent=parent)

    def set_expanded(self, expanded: bool) -> None:  # 旧签名（无 animated 参数）
        super().set_expanded(expanded)


class _GroupsEditor(GroupsTableEditor):
    """旧分组编辑器（兼容别名）：旧构造接 ParamSpec，新实现接 GroupColumn 列表。"""

    def __init__(self, spec, prefill, parent=None):
        _warnings.warn(
            "_GroupsEditor 已废弃，请改用 ui.widgets.groups_editor.GroupsTableEditor",
            DeprecationWarning, stacklevel=2)
        columns = [
            GroupColumn(c.key, c.label, c.unit, c.minimum, c.maximum,
                        c.decimals, float(c.default))
            for c in spec.columns
        ]
        rows = prefill if isinstance(prefill, list) else []
        super().__init__(columns, prefill=rows, parent=parent)


def __getattr__(name: str):
    if name == "DIALOG_QSS":
        _warnings.warn(
            "DIALOG_QSS 已废弃，请改用 ui.theme.apply_qss(dlg, 'dialog')",
            DeprecationWarning, stacklevel=2)
        return load_qss("dialog")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CollapsibleGroupBox", "DIALOG_QSS", "ItemParamsDialog",
    "_GroupsEditor", "GroupsTableEditor", "GroupColumn",
]
