# -*- coding: utf-8 -*-
"""saved_results 冒烟校验：保存 → 列表 → 聚合导出（落盘到临时目录，不污染 Results）。

重点校验：原始文件按正常运行输出目录布局（{item_key}.csv 在根、截图在
screenshots/）还原进 final 聚合目录，与直接生成的报告目录一致。

运行：.venv\\Scripts\\python.exe tests\\check_saved_results.py
"""
from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import debug_config  # noqa: E402

debug_config.REPORT_PDF_EXPORT = False  # 冒烟环境跳过 Edge 无头打印

from core.module_test import saved_results as sr  # noqa: E402
from core.module_test.result_model import ItemResult, ModuleTestResult  # noqa: E402

# 1x1 透明 PNG
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c626001000000ffff030000060005"
    "57bfabd40000000049454e44ae426082")


def _make_run_out_dir(tmp: str) -> tuple[str, str, str]:
    """模拟一次正常运行的输出目录：{item_key}.csv 在根、截图在 screenshots/。"""
    out_dir = os.path.join(tmp, "run_out")
    shot_dir = os.path.join(out_dir, "screenshots")
    os.makedirs(shot_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "ldo_ripple.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("Iload (mA),Vout (mV)\n0,1800.1\n100,1799.2\n")
    png_path = os.path.join(shot_dir, "ldo_ripple_100mA.png")
    with open(png_path, "wb") as f:
        f.write(_PNG_BYTES)
    return out_dir, csv_path, png_path


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="kk_saved_results_")
    sr.saved_root = lambda _m: os.path.join(tmp, "saved")  # type: ignore[attr-defined]
    sr.final_root = lambda _m: os.path.join(tmp, "final")  # type: ignore[attr-defined]

    run_out, csv_path, png_path = _make_run_out_dir(tmp)
    source = ModuleTestResult(
        module_type="ldo", chip_name="BES2800", module_name="LDO1",
        test_condition="25C", operator="tester", temperature="25",
        instruments=[{"name": "N6705C", "model": "N6705C", "sn": "SN1"}])
    source.summary["output_dir"] = run_out
    item = ItemResult(
        item_key="ldo_ripple", name="Load Capability&Ripple", unit="mV",
        passed=True,
        measured={"points": 2, "max_vpp_mv": 12.3,
                  "screenshots": [{"Iload (mA)": 100, "png": png_path}]},
        raw_csv_path=csv_path, waveform_png=png_path, notes="ok",
        ts="2026-09-09 10:00:00")

    # —— 保存（连存两次验证同秒不冲突 + 结构化落盘）——
    d1 = sr.save_item_result("ldo", item, source)
    d2 = sr.save_item_result("ldo", item, source)
    assert d1 != d2 and os.path.isfile(os.path.join(d1, "result.json"))
    assert os.path.isfile(os.path.join(d2, "result.json"))
    assert item.raw_csv_path == csv_path, "原 ItemResult 不得被改写"
    # 条目内资产按原输出目录相对布局落盘
    assert os.path.isfile(os.path.join(d1, "ldo_ripple.csv"))
    assert os.path.isfile(os.path.join(d1, "screenshots", "ldo_ripple_100mA.png"))

    # —— 列表 ——
    entries = sr.list_saved_results("ldo")
    assert len(entries) == 2, f"expect 2 entries, got {len(entries)}"
    e = entries[0]
    assert e["item_key"] == "ldo_ripple" and e["verdict"] == "PASS"
    assert e["chip_name"] == "BES2800" and e["module_name"] == "LDO1"

    # —— 聚合导出（勾选同项两次保存，验证文件名防覆盖）——
    html_path, pdf_path, out_dir = sr.export_saved_results(
        "ldo", [e["dir"] for e in entries])
    assert pdf_path is None
    assert os.path.isfile(html_path), html_path
    assert os.path.dirname(os.path.abspath(html_path)) == os.path.abspath(out_dir)
    # 原始文件按正常输出目录布局还原：CSV 在根、截图在 screenshots/
    assert os.path.isfile(os.path.join(out_dir, "ldo_ripple.csv")), \
        "final 目录缺根级原始 CSV"
    shots = os.listdir(os.path.join(out_dir, "screenshots"))
    assert len(shots) == 2, f"同项两次保存的截图应防覆盖共存: {shots}"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert "Load Capability&Ripple" in html, "报告应包含测试项标题"
    assert "BES2800" in html, "报告应包含芯片元信息"
    assert "data:image/png;base64," in html, "截图应内嵌进报告"
    # 单项 XLSX（openpyxl+Pillow 可用时）
    xlsx = os.path.join(out_dir, "XLSX", "ldo_ripple.xlsx")
    assert os.path.isfile(xlsx), f"单项 XLSX 缺失: {xlsx}"

    # —— 空选择报错 ——
    try:
        sr.export_saved_results("ldo", [])
    except ValueError:
        pass
    else:
        raise AssertionError("空选择应抛 ValueError")

    # —— 损坏条目容错 ——
    bad = os.path.join(tmp, "saved", "bad_item", "20260101_000000")
    os.makedirs(bad, exist_ok=True)
    with open(os.path.join(bad, "result.json"), "w", encoding="utf-8") as f:
        f.write("{not json")
    assert len(sr.list_saved_results("ldo")) == 2, "损坏条目应被跳过"

    print(f"SMOKE OK: 保存/列表/聚合导出(含原始文件布局还原)全部通过（{out_dir}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
