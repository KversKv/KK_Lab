"""TestPlanModel / TestPlanPanel 行为测试（P2 验收）。

无头（offscreen）运行：
    python tests/test_test_plan_model.py          # 直跑
    pytest tests/test_test_plan_model.py          # pytest
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.models.test_plan_model import (
    COL_CHECK, COL_STATUS, KeyRole, ST_FAIL, ST_IDLE, ST_NA, ST_PASS,
    ST_RUNNING, ST_SCOPE_MISSING, ST_UNSELECTED, ST_WAITING, StatusRole,
    TestPlanModel,
)

_app = QApplication.instance() or QApplication(sys.argv)


def _run(ctx):  # noqa: ANN001 - 假 run_fn
    return {}


REGISTRY = {
    "ldo_line_reg": ("Line Regulation", _run, False, True, []),
    "ldo_load_transient": ("Load Transient", _run, True, True, ["p"]),
    "ldo_quiescent": ("Quiescent", _run, False, False, []),
    "ldo_psrr": ("PSRR", _run, True, False, []),
}
STANDALONE = ("ldo_psrr",)


def _make() -> TestPlanModel:
    return TestPlanModel(REGISTRY, STANDALONE)


def _item_index(model: TestPlanModel, key: str, col: int = 0):
    for g in range(model.rowCount()):
        gidx = model.index(g, 0)
        for r in range(model.rowCount(gidx)):
            idx = model.index(r, col, gidx)
            if idx.data(KeyRole) == key:
                return idx
    raise AssertionError(f"item {key} not found")


# ------------------------------------------------------------------ 构建
def test_two_groups_built():
    m = _make()
    assert m.rowCount() == 2  # 自动 + 单项
    auto = m.index(0, 0)
    stand = m.index(1, 0)
    assert m.rowCount(auto) == 3
    assert m.rowCount(stand) == 1
    assert "自动测试序列" in m.index(0, 1).data(Qt.DisplayRole)
    assert "单项测试" in m.index(1, 1).data(Qt.DisplayRole)


def test_default_checked_from_registry():
    m = _make()
    assert set(m.selected_keys()) == {"ldo_line_reg", "ldo_load_transient"}
    assert m.stats() == (2, 4)


# ------------------------------------------------------------------ 勾选
def test_item_toggle_and_group_tristate():
    m = _make()
    auto = m.index(0, 0)
    # 初始：3 项中 2 项勾选 → 分组半选
    assert auto.data(Qt.CheckStateRole) == Qt.PartiallyChecked
    # 勾上剩余项 → 全选
    idx = _item_index(m, "ldo_quiescent", COL_CHECK)
    m.setData(idx, Qt.Checked, Qt.CheckStateRole)
    assert auto.data(Qt.CheckStateRole) == Qt.Checked
    # 分组反选 → 全不选
    m.setData(auto.siblingAtColumn(COL_CHECK), Qt.Unchecked, Qt.CheckStateRole)
    assert m.selected_keys() == []


def test_toggle_all_auto_full_cycle():
    m = _make()
    target = m.toggle_all_auto()
    assert target is True
    assert set(m.selected_keys()) == {"ldo_line_reg", "ldo_load_transient", "ldo_quiescent"}
    # 单项测试分组不受影响
    assert "ldo_psrr" not in m.selected_keys()
    target = m.toggle_all_auto()
    assert target is False
    assert m.selected_keys() == []


def test_set_checked_keys():
    m = _make()
    m.set_checked_keys({"ldo_psrr"})
    assert m.selected_keys() == ["ldo_psrr"]


# ------------------------------------------------------------------ 示波器联动
def test_scope_missing_status_and_restore():
    m = _make()
    m.set_scope_connected(False)
    assert _item_index(m, "ldo_load_transient", COL_STATUS).data(StatusRole) == ST_SCOPE_MISSING
    assert _item_index(m, "ldo_psrr", COL_STATUS).data(StatusRole) == ST_SCOPE_MISSING
    # 非示波器项不受影响
    assert _item_index(m, "ldo_line_reg", COL_STATUS).data(StatusRole) == ST_IDLE
    m.set_scope_connected(True)
    assert _item_index(m, "ldo_load_transient", COL_STATUS).data(StatusRole) == ST_IDLE


# ------------------------------------------------------------------ 运行态
def test_run_state_flow():
    m = _make()
    m.enter_run_state(["ldo_line_reg"])
    assert _item_index(m, "ldo_line_reg", COL_STATUS).data(StatusRole) == ST_WAITING
    assert _item_index(m, "ldo_psrr", COL_STATUS).data(StatusRole) == ST_UNSELECTED
    # 运行期勾选锁定
    flags = m.flags(_item_index(m, "ldo_line_reg", COL_CHECK))
    assert not (flags & Qt.ItemIsUserCheckable)
    assert not m.setData(_item_index(m, "ldo_line_reg", COL_CHECK), Qt.Unchecked, Qt.CheckStateRole)

    m.mark_item_running("ldo_line_reg")
    assert _item_index(m, "ldo_line_reg", COL_STATUS).data(StatusRole) == ST_RUNNING
    m.mark_item_done("ldo_line_reg", "PASS")
    idx = _item_index(m, "ldo_line_reg", COL_STATUS)
    assert idx.data(StatusRole) == ST_PASS
    m.exit_run_state()
    assert _item_index(m, "ldo_line_reg", COL_STATUS).data(StatusRole) == ST_IDLE
    flags = m.flags(_item_index(m, "ldo_line_reg", COL_CHECK))
    assert flags & Qt.ItemIsUserCheckable


def test_mark_done_verdicts():
    m = _make()
    m.enter_run_state(["a", "b"])
    m.mark_item_done("ldo_line_reg", "FAIL")
    assert _item_index(m, "ldo_line_reg", COL_STATUS).data(StatusRole) == ST_FAIL
    m.mark_item_done("ldo_quiescent", "N/A")
    assert _item_index(m, "ldo_quiescent", COL_STATUS).data(StatusRole) == ST_NA
    assert m.failed_keys() == ["ldo_line_reg"]


def test_scope_change_during_run_does_not_clobber():
    m = _make()
    m.enter_run_state(["ldo_load_transient"])
    m.set_scope_connected(False)  # 运行期不得覆盖状态列
    assert _item_index(m, "ldo_load_transient", COL_STATUS).data(StatusRole) == ST_WAITING


# ------------------------------------------------------------------ override 标记
def test_customized_flag():
    m = _make()
    m.set_item_customized("ldo_load_transient", True)
    assert m.customized_keys() == ["ldo_load_transient"]
    m.set_item_customized("ldo_load_transient", False)
    assert m.customized_keys() == []


# ------------------------------------------------------------------ 过滤代理
def test_filter_proxy_needle_and_only_failed():
    from ui.pages.module_test._sections.test_plan_panel import _PlanFilterProxy

    m = _make()
    proxy = _PlanFilterProxy()
    proxy.setSourceModel(m)

    def visible_keys():
        out = []
        for g in range(proxy.rowCount()):
            gidx = proxy.index(g, 0)
            for r in range(proxy.rowCount(gidx)):
                out.append(proxy.index(r, 0, gidx).data(KeyRole))
        return out

    assert len(visible_keys()) == 4
    proxy.set_needle("load")
    assert visible_keys() == ["ldo_load_transient"]
    proxy.set_needle("")

    m.enter_run_state(["ldo_line_reg", "ldo_quiescent"])
    m.mark_item_done("ldo_line_reg", "FAIL")
    proxy.set_only_failed(True)
    assert visible_keys() == ["ldo_line_reg"]


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted({k: v for k, v in globals().items()
                            if k.startswith("test_")}.items()):
        try:
            fn()
            print(f"PASS {name}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {name}: {exc}")
    sys.exit(1 if failures else 0)
