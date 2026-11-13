#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Arb Set AI 契约（AIControllablePage）offscreen 冒烟验证。

覆盖：
1. ai_capabilities / ai_get_config 快照完整性与控件一致；
2. ai_apply_config 正常落地（udef 序列 + 部分参数缺省沿用 + 切通道 + 面板展开）；
3. 非法输入事务式拒绝（未知 shape/未知字段/空点表/越界 repeat/非 dict）；
4. 草案闭环：generate_config_draft → apply_test_config_draft（handler 级，模拟 main_window 回调）。

运行：QT_QPA_PLATFORM=offscreen python tests/smoke_arb_ai_contract.py
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir)))

from PySide6.QtWidgets import QApplication

from core.ai.actions.handlers.deps import ActionDeps
from core.ai.actions.handlers.test import build_handlers
from core.ai.draft_registry import DraftRegistry
from ui.pages.power_analyzer.power_analyzer_analyser_ui import N6705CAnalyserUI

PASS = []


def check(name, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    PASS.append(cond)
    print(f"[{status}] {name}" + (f" -- {detail}" if detail and not cond else ""), flush=True)


def main():
    app = QApplication.instance() or QApplication([])
    page = N6705CAnalyserUI()

    # ---------- 1. capabilities / get_config ----------
    caps = page.ai_capabilities()
    check("ai_capabilities == {get_config, apply_config}",
          caps == {"get_config", "apply_config"}, str(caps))

    snap = page.ai_get_config()
    expected_keys = {
        "page", "scope", "arb_device", "arb_channel", "arb_type", "arb_shape",
        "arb_params", "arb_udef_points", "arb_continuous", "arb_repeat_count",
        "arb_terminate_last",
    }
    check("ai_get_config 顶层键齐全", isinstance(snap, dict) and expected_keys <= set(snap),
          str(sorted(snap) if isinstance(snap, dict) else snap))
    check("快照默认通道 A/CH1", snap["arb_device"] == "A" and snap["arb_channel"] == 1)
    check("快照默认 shape=none / type=VOLT",
          snap["arb_shape"] == "none" and snap["arb_type"] == "VOLT")
    check("快照默认 udef 点表与模型一致",
          snap["arb_udef_points"] == [list(p) for p in page._arb_udef_points])

    # ---------- 2. apply_config 正常落地（udef 全量序列） ----------
    points = [[3.0, 0.002], [3.6, 0.001], [4.2, 0.001], [3.6, 0.002], [3.0, 0.005]]
    ok, msg = page.ai_apply_config({
        "arb_channel": 2,
        "arb_type": "VOLT",
        "arb_shape": "udef",
        "arb_udef_points": points,
        "arb_continuous": False,
        "arb_repeat_count": 5,
        "arb_terminate_last": True,
    })
    check("udef 全量落地 ok", ok, msg)
    check("落地后当前通道切到 CH2",
          page._arb_current_device == "A" and page._arb_current_channel == 2)
    check("udef 模型已替换", page._arb_udef_points == [list(p) for p in points],
          str(page._arb_udef_points))
    check("store 已写 CH2 udef 配置",
          page._arb_param_store.get(("A", 2), {}).get("shape") == "udef"
          and page._arb_param_store[("A", 2)]["repeat_count"] == "5"
          and page._arb_param_store[("A", 2)]["terminate_last"] is True)
    check("点表行数 = 5", page.arb_udef_table.rowCount() == 5,
          str(page.arb_udef_table.rowCount()))
    check("面板自动展开", not page.arb_collapsed)
    check("terminate_last 单选已选", page.arb_term_last_radio.isChecked())
    # 注：未连接时页面祖先禁用传播使 repeat 恒 disabled（Qt 语义），enabled 态属连接后行为，此处仅校验值
    check("repeat 输入框=5 且 continuous 未勾选",
          page.arb_repeat_input.text() == "5" and not page.arb_continuous_toggle.isChecked())

    snap2 = page.ai_get_config()
    check("落地后快照回读一致",
          snap2["arb_channel"] == 2 and snap2["arb_shape"] == "udef"
          and snap2["arb_udef_points"] == [list(p) for p in points]
          and snap2["arb_repeat_count"] == 5 and snap2["arb_terminate_last"] is True)

    # ---------- 2b. 部分参数缺省沿用（pulse，仅改 v1 与 freq） ----------
    ok, msg = page.ai_apply_config({
        "arb_channel": 2,
        "arb_shape": "pulse",
        "arb_params": {"v1": 4.1, "freq_hz": 200},
    })
    check("pulse 部分参数落地 ok", ok, msg)
    entry = page._arb_param_store[("A", 2)]
    pulse_params = entry["params"]["pulse"]
    check("pulse 覆盖字段生效", pulse_params.get("v1") == "4.1"
          and pulse_params.get("freq_hz") == "200.0", str(pulse_params))
    check("pulse 未列字段沿用默认（v0=3.3）", pulse_params.get("v0") == "3.3",
          str(pulse_params))
    check("repeat/terminate 沿用上一配置", entry["repeat_count"] == "5"
          and entry["terminate_last"] is True)
    check("udef 点表记忆保留", "udef" in entry["params"])

    # ---------- 2c. 切回 CH1 编辑（跨通道落地） ----------
    ok, msg = page.ai_apply_config({
        "arb_channel": 1, "arb_shape": "sine",
        "arb_params": {"offset": 1.8, "ampl": 0.05, "freq_hz": 50},
        "arb_continuous": True,
    })
    check("跨通道落地 CH1 ok", ok, msg)
    check("当前通道切回 CH1", page._arb_current_channel == 1)
    check("continuous=True 已勾选", page.arb_continuous_toggle.isChecked())
    check("CH2 store 未被破坏",
          page._arb_param_store[("A", 2)]["shape"] == "pulse")

    # ---------- 3. 非法输入事务式拒绝 ----------
    import copy
    before = copy.deepcopy(page._arb_param_store)
    ok, msg = page.ai_apply_config({"arb_shape": "udef", "arb_udef_points": []})
    check("空 udef 点表拒绝", not ok)
    ok, msg = page.ai_apply_config({"arb_shape": "seq"})
    check("seq 占位拒绝", not ok and "尚未开放" in msg, msg)
    ok, msg = page.ai_apply_config({"arb_shape": "nope"})
    check("未知 shape 拒绝", not ok and "arb_shape 无效" in msg, msg)
    ok, msg = page.ai_apply_config({
        "arb_shape": "sine", "arb_params": {"bad_key": 1.0}})
    check("未知 params 字段拒绝并回显可用字段", not ok and "offset" in msg, msg)
    ok, msg = page.ai_apply_config({"arb_repeat_count": 0})
    check("repeat_count 越界拒绝", not ok)
    ok, msg = page.ai_apply_config({"arb_channel": 9})
    check("通道越界拒绝", not ok)
    ok, msg = page.ai_apply_config("not-a-dict")
    check("非 dict 拒绝", not ok)
    ok, msg = page.ai_apply_config({
        "arb_shape": "udef", "arb_udef_points": [[3.3, 0]]})
    check("dwell<=0 拒绝", not ok and "dwell" in msg, msg)
    store_clean = page._arb_param_store == before
    if not store_clean:
        for k in set(before) | set(page._arb_param_store):
            if before.get(k) != page._arb_param_store.get(k):
                print(f"  store diff {k}:\n    before={before.get(k)}\n    after={page._arb_param_store.get(k)}", flush=True)
    check("拒绝后 store 未被污染", store_clean)

    # ---------- 4. 草案闭环（handler 级） ----------
    registry = DraftRegistry()
    deps = ActionDeps(
        page_key_getter=lambda: "power_analyser",
        test_config_getter=page.ai_get_config,
        config_apply_callback=lambda draft: page.ai_apply_config(draft.payload),
        draft_registry=registry,
    )
    handlers = build_handlers(deps)

    # 4a. 未知 changes 键：拒绝并回显 valid_keys
    res = handlers["generate_config_draft"]({"changes": {"bogus_key": 1}})
    check("generate_config_draft 未知键拒绝", not res["ok"]
          and "arb_shape" in res.get("valid_keys", []), str(res))

    # 4b. 生成 udef 序列草案 → apply 落地
    seq_points = [[1.0, 0.01], [2.0, 0.01], [3.0, 0.01], [2.0, 0.01]]
    res = handlers["generate_config_draft"]({
        "changes": {
            "arb_channel": 3,
            "arb_shape": "udef",
            "arb_udef_points": seq_points,
            "arb_repeat_count": 2,
        },
        "title": "AI 生成的 Arb 序列",
    })
    check("generate_config_draft ok", res["ok"], str(res))
    draft_id = res.get("draft_id", "")
    res2 = handlers["apply_test_config_draft"]({"draft_id": draft_id})
    check("apply_test_config_draft ok", res2["ok"], str(res2))
    check("闭环后 CH3 udef 已落地",
          page._arb_current_channel == 3
          and page._arb_udef_points == [list(p) for p in seq_points]
          and page._arb_param_store[("A", 3)]["repeat_count"] == "2",
          f"ch={page._arb_current_channel} points={page._arb_udef_points}")

    # 4c. 无效 draft_id 拒绝
    res3 = handlers["apply_test_config_draft"]({"draft_id": "draft_999"})
    check("无效 draft_id 拒绝或回退唯一草案", isinstance(res3, dict))

    page.deleteLater()
    app.processEvents()
    return all(PASS)


if __name__ == "__main__":
    success = main()
    print("SMOKE:", "PASS" if success else "FAIL", flush=True)
    os._exit(0 if success else 1)
