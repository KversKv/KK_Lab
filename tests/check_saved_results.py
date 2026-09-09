# -*- coding: utf-8 -*-
"""saved_results 冒烟校验：保存(覆盖) → 列表(过滤) → 聚合导出（临时目录，不污染 Results）。

重点校验：
- 目录按 saved/{芯片}/{模块}/{item_key}/ 分层；
- 同芯片同模块覆盖保存，每项只维护一套（内容为最新）；
- list_saved_results 按芯片/模块过滤；
- 原始文件按正常运行输出目录布局还原进 final 聚合目录，不同条目同名文件防覆盖。

运行：.venv\\Scripts\\python.exe tests\\check_saved_results.py
"""
from __future__ import annotations

import json
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


def _make_run_out_dir(tmp: str, tag: str, item_key: str,
                      shot_name: str) -> tuple[str, str, str]:
    """模拟一次正常运行的输出目录：{item_key}.csv 在根、截图在 screenshots/。"""
    out_dir = os.path.join(tmp, f"run_out_{tag}")
    shot_dir = os.path.join(out_dir, "screenshots")
    os.makedirs(shot_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, f"{item_key}.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("Iload (mA),Vout (mV)\n0,1800.1\n100,1799.2\n")
    png_path = os.path.join(shot_dir, shot_name)
    with open(png_path, "wb") as f:
        f.write(_PNG_BYTES)
    return out_dir, csv_path, png_path


def _source(chip: str, module: str, out_dir: str) -> ModuleTestResult:
    src = ModuleTestResult(
        module_type="ldo", chip_name=chip, module_name=module,
        test_condition="25C", operator="tester", temperature="25",
        instruments=[{"name": "N6705C", "model": "N6705C", "sn": "SN1"}])
    src.summary["output_dir"] = out_dir
    return src


def _item(item_key: str, name: str, csv_path: str, png_path: str,
          max_vpp: float, ts: str) -> ItemResult:
    return ItemResult(
        item_key=item_key, name=name, unit="mV", passed=True,
        measured={"points": 2, "max_vpp_mv": max_vpp,
                  "screenshots": [{"Iload (mA)": 100, "png": png_path}]},
        raw_csv_path=csv_path, waveform_png=png_path, notes="ok", ts=ts)


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="kk_saved_results_")
    sr.saved_root = lambda _m: os.path.join(tmp, "saved")  # type: ignore[attr-defined]
    sr.final_root = lambda _m: os.path.join(tmp, "final")  # type: ignore[attr-defined]

    # —— 覆盖保存：同芯片同模块连存两次，目录同一、内容最新 ——
    out_a, csv_a, png_a = _make_run_out_dir(tmp, "a", "ldo_ripple", "same.png")
    src_a = _source("BES2800", "LDO1", out_a)
    d1 = sr.save_item_result("ldo", _item("ldo_ripple", "Load Capability&Ripple",
                                          csv_a, png_a, 12.3,
                                          "2026-09-09 10:00:00"), src_a)
    d2 = sr.save_item_result("ldo", _item("ldo_ripple", "Load Capability&Ripple",
                                          csv_a, png_a, 99.9,
                                          "2026-09-09 11:00:00"), src_a)
    assert d1 == d2, f"覆盖保存应同一目录: {d1} != {d2}"
    expect = os.path.join(tmp, "saved", "BES2800", "LDO1", "ldo_ripple")
    assert os.path.abspath(d1) == os.path.abspath(expect), d1
    with open(os.path.join(d1, "result.json"), "r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload["item"]["measured"]["max_vpp_mv"] == 99.9, "内容应为最新一次"
    # 条目内资产按原输出目录相对布局落盘
    assert os.path.isfile(os.path.join(d1, "ldo_ripple.csv"))
    assert os.path.isfile(os.path.join(d1, "screenshots", "same.png"))

    # —— 同模块第二项（截图同名，验导出防覆盖）+ 另一芯片/模块的项 ——
    out_b, csv_b, png_b = _make_run_out_dir(tmp, "b", "ldo_line_reg", "same.png")
    src_b = _source("BES2800", "LDO1", out_b)
    sr.save_item_result("ldo", _item("ldo_line_reg", "Line Regulation",
                                     csv_b, png_b, 1.1,
                                     "2026-09-09 10:30:00"), src_b)
    out_c, csv_c, png_c = _make_run_out_dir(tmp, "c", "ldo_ripple", "c.png")
    src_c = _source("BES2810", "LDO2", out_c)
    sr.save_item_result("ldo", _item("ldo_ripple", "Load Capability&Ripple",
                                     csv_c, png_c, 2.2,
                                     "2026-09-09 09:00:00"), src_c)

    # —— 列表：过滤 + 全覆盖 ——
    scoped = sr.list_saved_results("ldo", "BES2800", "LDO1")
    assert {e["item_key"] for e in scoped} == {"ldo_ripple", "ldo_line_reg"}, scoped
    all_e = sr.list_saved_results("ldo")
    assert len(all_e) == 3, f"expect 3 entries, got {len(all_e)}"
    chip_only = sr.list_saved_results("ldo", chip_name="BES2810")
    assert len(chip_only) == 1 and chip_only[0]["module_name"] == "LDO2"
    none = sr.list_saved_results("ldo", "NO_CHIP", "NO_MODULE")
    assert none == []

    # —— 聚合导出（勾选同模块两项：截图同名应防覆盖共存）——
    html_path, pdf_path, out_dir = sr.export_saved_results(
        "ldo", [e["dir"] for e in scoped])
    assert pdf_path is None
    assert os.path.isfile(html_path), html_path
    assert os.path.dirname(os.path.abspath(html_path)) == os.path.abspath(out_dir)
    # 原始文件按正常输出目录布局还原：CSV 在根、截图在 screenshots/
    assert os.path.isfile(os.path.join(out_dir, "ldo_ripple.csv")), \
        "final 目录缺根级原始 CSV"
    assert os.path.isfile(os.path.join(out_dir, "ldo_line_reg.csv"))
    shots = sorted(os.listdir(os.path.join(out_dir, "screenshots")))
    assert len(shots) == 2, f"同名截图应防覆盖共存: {shots}"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert "Load Capability&Ripple" in html and "Line Regulation" in html
    assert "BES2800" in html, "报告应包含芯片元信息"
    assert "data:image/png;base64," in html, "截图应内嵌进报告"
    # 单项 XLSX（openpyxl+Pillow 可用时）
    assert os.path.isfile(os.path.join(out_dir, "XLSX", "ldo_ripple.xlsx"))

    # —— 空选择报错 ——
    try:
        sr.export_saved_results("ldo", [])
    except ValueError:
        pass
    else:
        raise AssertionError("空选择应抛 ValueError")

    # —— 损坏条目容错 ——
    bad = os.path.join(tmp, "saved", "BES2800", "LDO1", "bad_item")
    os.makedirs(bad, exist_ok=True)
    with open(os.path.join(bad, "result.json"), "w", encoding="utf-8") as f:
        f.write("{not json")
    assert len(sr.list_saved_results("ldo", "BES2800", "LDO1")) == 2, "损坏条目应被跳过"

    print(f"SMOKE OK: 覆盖保存/过滤列表/聚合导出(含布局还原+防覆盖)全部通过（{out_dir}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
