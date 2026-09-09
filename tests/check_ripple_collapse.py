#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load Capability & Ripple 带载拐点（Vout 崩溃）数据处理校验。

用例（A/B 数据来自真机回归：240mA 后带载能力崩溃，Vout 跌到 ~68mV）：
  A. 崩溃场景：拐点=240mA；260mA 起 5 行无效——不参与 Max Vpp / Max Vout
     Drop，Max Load=240mA；measured 带 collapse_vout_threshold_mv；
  B. 崩溃点 Vpp 异常放大（50mV）：Max Vpp 仍取有效段（修复前会取崩溃点）；
  C. 无崩溃线性场景：Max Load=末点，无 collapse_vout_threshold_mv 键；
  D. 报告侧：_build_rules 生成 Vout 列 lt/fail 规则且崩溃行全命中（前端
     整行标红）、有效行不误伤；_build_metrics 含 Max Load 标签。

用法：.venv\\Scripts\\python.exe tests\\check_ripple_collapse.py
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import core.module_test._common as common  # noqa: E402
from core.module_test._common import ItemContext, run_load_capability_ripple  # noqa: E402
from core.module_test.report import _build_metrics, _build_rules, _build_table  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


# 真机回归数据（0~340mA 步进 20；260mA 起 Vout 崩溃）
ILOADS = [float(i) for i in range(0, 341, 20)]
VOUTS = [1202.243, 1193.101, 1185.734, 1178.905, 1171.739, 1164.092,
         1154.536, 1143.346, 1129.936, 1115.342, 1102.793, 1088.652,
         1065.101, 68.05, 69.615, 69.446, 68.72, 68.602]
VPPS = [2.7, 2.7, 2.7, 2.7, 2.7, 2.7, 2.7, 2.7, 2.7, 2.7, 2.7, 2.7, 2.7,
        2.0, 2.7, 2.7, 2.7, 2.0]
RMSS = [0.319, 0.315, 0.346, 0.318, 0.34, 0.346, 0.342, 0.341, 0.355,
        0.352, 0.341, 0.333, 0.342, 0.347, 0.339, 0.333, 0.299, 0.343]

LOGS: list[str] = []


def _run(vouts, vpps, nominal_mv=1200.0):
    """mock 路径跑 run_load_capability_ripple，mock_jitter 按序喂给定数据。"""
    seq = iter(v for triple in zip(vouts, vpps, RMSS) for v in triple)
    orig = common.mock_jitter
    common.mock_jitter = lambda _base, _ratio=0.02: next(seq)
    out_dir = tempfile.mkdtemp(prefix="kk_ripple_check_")
    try:
        ctx = ItemContext(
            n6705c=None, scope=object(), chamber=None,
            config={"vout_nominal_mv": nominal_mv,
                    "iload_start_ma": 0, "iload_end_ma": 340, "iload_step_ma": 20},
            out_dir=out_dir, is_mock=True,
            stop_flag_fn=lambda: False,
            log_fn=LOGS.append, progress_fn=lambda _p, _t: None)
        return run_load_capability_ripple(ctx, "ldo_ripple",
                                          "Load Capability&Ripple", 2.7, 0.34)
    finally:
        common.mock_jitter = orig
        shutil.rmtree(out_dir, ignore_errors=True)


# ---- 用例 A：崩溃场景指标 ----
res = _run(VOUTS, VPPS)
m = res.measured
check("A 拐点 Max Load=240mA", m.get("max_load_ma") == 240.0,
      f"max_load_ma={m.get('max_load_ma')}")
check("A 有效点数 13/18", m.get("valid_points") == 13 and m.get("points") == 18,
      f"valid={m.get('valid_points')}/{m.get('points')}")
check("A Max Vpp 取自有效段", m.get("max_vpp_mv") == 2.7
      and m.get("max_vpp_at_ma") <= 240.0,
      f"max_vpp={m.get('max_vpp_mv')}@{m.get('max_vpp_at_ma')}mA")
expect_drop = round(1200.0 - 1065.101, 4)
check("A Max Vout Drop 不含崩溃段", m.get("max_vout_drop_mv") == expect_drop,
      f"drop={m.get('max_vout_drop_mv')} (崩溃段会得 {1200.0 - 68.05:.4f})")
expect_thr = round((1065.101 + 68.05) / 2.0, 4)
check("A 崩溃阈值=拐点前后中点", m.get("collapse_vout_threshold_mv") == expect_thr,
      f"threshold={m.get('collapse_vout_threshold_mv')}")
check("A 日志提示崩溃剔除",
      any("Max Load=240mA" in s and "无效" in s for s in LOGS))

# ---- 用例 B：崩溃点 Vpp 异常放大也不污染 Max Vpp ----
vpps_bad = list(VPPS)
vpps_bad[13] = 50.0  # 260mA 崩溃点 Vpp 放大
res_b = _run(VOUTS, vpps_bad)
check("B 崩溃点 Vpp=50 不参与 Max Vpp",
      res_b.measured.get("max_vpp_mv") == 2.7
      and res_b.measured.get("max_vpp_at_ma") <= 240.0,
      f"max_vpp={res_b.measured.get('max_vpp_mv')}@{res_b.measured.get('max_vpp_at_ma')}mA")

# ---- 用例 C：线性无崩溃 ----
vouts_lin = [1200.0 - il * 0.2 for il in ILOADS]  # 全程线性缓降
res_c = _run(vouts_lin, VPPS)
mc = res_c.measured
check("C 无崩溃 Max Load=末点 340mA", mc.get("max_load_ma") == 340.0,
      f"max_load_ma={mc.get('max_load_ma')}")
check("C 无崩溃不带阈值键", "collapse_vout_threshold_mv" not in mc)
check("C 全部点有效", mc.get("valid_points") == 18,
      f"valid={mc.get('valid_points')}")

# ---- 用例 D：报告侧规则与指标 ----
out_dir = tempfile.mkdtemp(prefix="kk_ripple_check_")
try:
    res.raw_csv_path = os.path.join(out_dir, "ldo_ripple.csv")
    common.write_csv(res.raw_csv_path,
                     ["Iload (mA)", "Vout (mV)", "Vpp (mV)", "RMS (mV)"],
                     [list(r) for r in zip(ILOADS, VOUTS, VPPS, RMSS)])
    table = _build_table(res)
    rules = _build_rules(res, table)
    lt_rules = [r for r in rules if r.get("op") == "lt"]
    check("D 生成 Vout 列 lt/fail 标红规则", len(lt_rules) == 1
          and lt_rules[0].get("level") == "fail"
          and lt_rules[0].get("value") == expect_thr,
          f"rules={lt_rules}")
    if table and lt_rules:
        ci = next(i for i, c in enumerate(table["columns"])
                  if c["key"] == lt_rules[0]["column"])
        col_label = table["columns"][ci]["label"]
        hit = [i for i, row in enumerate(table["data"])
               if isinstance(row[ci], (int, float))
               and row[ci] < lt_rules[0]["value"]]
        check("D 标红列=Vout 且恰命中 260mA 起 5 行",
              col_label == "Vout" and hit == [13, 14, 15, 16, 17],
              f"col={col_label}, hit_rows={hit}")
    metrics = _build_metrics(res, table)
    ml = next((x for x in metrics if x["key"] == "max_load"), None)
    check("D metrics 含 Max Load=240mA 标签",
          ml is not None and ml["value"] == 240.0 and ml["unit"] == "mA",
          f"metrics={[(x['key'], x['value']) for x in metrics]}")
finally:
    shutil.rmtree(out_dir, ignore_errors=True)

print(f"\n{'全部通过' if not FAILURES else '失败: ' + ', '.join(FAILURES)}")
sys.exit(1 if FAILURES else 0)
