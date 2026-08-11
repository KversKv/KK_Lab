"""ItemParamsDialog override 语义单测（任务书硬验收：三条契约全覆盖）。

契约：
1. 无 base_key 的项级参数 → get_override() 全量返回（显示即生效）；
2. 有 base_key 的参数 → 与预填 diff（相同不返回，运行时回退基类 cfg）；
3. msb/lsb/max_code 同时存在 → max_code 自动算 (1 << (msb-lsb+1)) - 1。

    python tests/test_item_params_dialog.py
    pytest tests/test_item_params_dialog.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDoubleSpinBox, QLineEdit, QSpinBox

from ui.pages.module_test.dialogs.judge_dialog import JudgeCriteriaTab

from core.module_test.param_spec import ParamSpec
from ui.pages.module_test.dialogs.item_params_dialog import ItemParamsDialog

_app = QApplication.instance() or QApplication(sys.argv)


def _dlg(specs, override=None, base_fn=None):
    return ItemParamsDialog(
        title="t", specs=specs,
        current_override=override or {},
        base_value_fn=base_fn or (lambda _k: None),
        parent=None)


# ------------------------------------------------------------------ 契约 1
def test_no_base_key_returns_full():
    specs = [
        ParamSpec("reg_addr", "寄存器", "int", 0x10, "", minimum=0, maximum=0xFF),
        ParamSpec("msb", "MSB", "int", 7, "", minimum=0, maximum=31),
        ParamSpec("lsb", "LSB", "int", 0, "", minimum=0, maximum=31),
    ]
    dlg = _dlg(specs)
    out = dlg.get_override()
    assert out == {"reg_addr": 0x10, "msb": 7, "lsb": 0}, out


# ------------------------------------------------------------------ 契约 2
def test_base_key_diff_semantics():
    specs = [
        ParamSpec("settle_time_s", "稳定时间", "float", 0.05, "s",
                  base_key="settle_time_s", minimum=0, maximum=60, decimals=3),
        ParamSpec("average_cnt", "平均次数", "int", 3, "",
                  base_key="average_cnt", minimum=1, maximum=100),
    ]
    # 预填 = 基类值；不改 → 不返回（运行时回退基类）
    dlg = _dlg(specs, base_fn=lambda k: {"settle_time_s": 0.05, "average_cnt": 3}[k])
    assert dlg.get_override() == {}, dlg.get_override()
    # 改了 settle → 仅返回改动项
    dlg2 = _dlg(specs, base_fn=lambda k: {"settle_time_s": 0.05, "average_cnt": 3}[k])
    dlg2._editors["settle_time_s"].setValue(0.2)
    out = dlg2.get_override()
    assert out == {"settle_time_s": 0.2}, out
    # current_override 优先于 base_key 预填
    dlg3 = _dlg(specs, override={"average_cnt": 7},
                base_fn=lambda k: {"settle_time_s": 0.05, "average_cnt": 3}[k])
    assert dlg3._editors["average_cnt"].value() == 7


# ------------------------------------------------------------------ 契约 3
def test_max_code_autocalc():
    specs = [
        ParamSpec("reg_addr", "寄存器", "int", 0x10, "", minimum=0, maximum=0xFF),
        ParamSpec("msb", "MSB", "int", 7, "", minimum=0, maximum=31),
        ParamSpec("lsb", "LSB", "int", 0, "", minimum=0, maximum=31),
        ParamSpec("max_code", "Code 结束", "int", 255, "", minimum=0, maximum=65535),
    ]
    dlg = _dlg(specs)
    # 初始 msb=7, lsb=0 → max_code = (1<<8)-1 = 255
    assert dlg._editors["max_code"].value() == 255
    # 改 msb=9 → max_code = (1<<10)-1 = 1023
    dlg._editors["msb"].setValue(9)
    assert dlg._editors["max_code"].value() == 1023
    # 改 lsb=2（msb=9）→ max_code = (1<<8)-1 = 255
    dlg._editors["lsb"].setValue(2)
    assert dlg._editors["max_code"].value() == 255
    # max_code 无 base_key → get_override 全量返回（含自动算出的值）
    out = dlg.get_override()
    assert out["max_code"] == 255 and out["msb"] == 9 and out["lsb"] == 2


# ------------------------------------------------------------------ 文本/组合
def test_text_prefill_list_and_get():
    spec = ParamSpec("freq_points", "频点", "text", "", "", hint="逗号分隔")
    dlg = _dlg([spec], override={"freq_points": [10, 100, 1000]})
    editor = dlg._editors["freq_points"]
    assert isinstance(editor, QLineEdit)
    assert editor.text() == "10, 100, 1000"
    assert dlg.get_override() == {"freq_points": "10, 100, 1000"}


def test_editor_types():
    specs = [
        ParamSpec("a", "A", "int", 1, ""),
        ParamSpec("b", "B", "float", 0.5, "", decimals=2),
        ParamSpec("c", "C", "text", "x", ""),
    ]
    dlg = _dlg(specs)
    assert isinstance(dlg._editors["a"], QSpinBox)
    assert isinstance(dlg._editors["b"], QDoubleSpinBox)
    assert isinstance(dlg._editors["c"], QLineEdit)


# ------------------------------------------------------------------ 判断标准页
def test_judge_tab_roundtrip():
    specs = [ParamSpec("average_cnt", "平均次数", "int", 3, "",
                       base_key="average_cnt", minimum=1, maximum=100)]
    payload = {"rules": [
        {"metric": "max_vpp_mv", "op": "<", "v1": 10.0, "v2": None},
    ]}
    dlg = _dlg(specs, base_fn=lambda _k: 3)
    # 无 item_key → 无判断标准页
    assert dlg._judge_tab is None
    assert dlg.get_judge_rules() == []

    dlg2 = ItemParamsDialog(
        title="t", specs=specs, current_override={},
        base_value_fn=lambda _k: 3, parent=None,
        item_key="ldo_ripple", judge_payload=payload)
    assert isinstance(dlg2._judge_tab, JudgeCriteriaTab)
    rules = dlg2.get_judge_rules()
    assert rules == [{"metric": "max_vpp_mv", "op": "<", "v1": 10.0,
                      "v2": None}], rules
    # 参数 override 语义不受判断标准页影响
    assert dlg2.get_override() == {}

    # 全部取消启用 → 空规则（外层据此清掉该项判定）
    dlg2._judge_tab._editors[0]["check"].setChecked(False)
    assert dlg2.get_judge_rules() == []

    # 无指标项（JUDGE_METRICS 未注册）→ 无判断标准页
    dlg3 = ItemParamsDialog(
        title="t", specs=specs, current_override={},
        base_value_fn=lambda _k: 3, parent=None,
        item_key="ldo_protection", judge_payload=None)
    assert dlg3._judge_tab is None


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
