"""Module Test 统一结果数据结构（规划 §7.1）。

纯数据 dataclass，禁依赖 Qt；供 runner 产出、report 渲染、UI 展示与 AI 摘要共用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ItemResult:
    """单测试项结果。

    Attributes:
        item_key: 测试项标识（如 ldo_vout_scan / dcdc_efficiency）。
        name: 可读名称。
        unit: 主测量值单位（如 mV / % / dB / mA）。
        passed: 判定结果；True=PASS，False=FAIL，None=仅记录不判定。
        measured: 关键测量值（dict 或 list[dict]，用于报告表格）。
        raw_csv_path: 原始数据 CSV 路径（None 表示未落盘）。
        waveform_png: 波形截图 PNG 路径（None 表示无波形）。
        notes: 备注/异常说明。
        ts: 完成时间戳（ISO 字符串）。
    """

    item_key: str
    name: str
    unit: str = ""
    passed: bool | None = None
    measured: Any = None
    raw_csv_path: str | None = None
    waveform_png: str | None = None
    notes: str = ""
    ts: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_summary(self) -> dict[str, Any]:
        verdict = "N/A" if self.passed is None else ("PASS" if self.passed else "FAIL")
        return {
            "item_key": self.item_key,
            "name": self.name,
            "unit": self.unit,
            "passed": verdict,
            "notes": self.notes,
            "raw_csv_path": self.raw_csv_path,
            "waveform_png": self.waveform_png,
        }


@dataclass
class ModuleTestResult:
    """一次 Module Test 执行的汇总结果。"""

    module_type: str  # "ldo" | "dcdc"
    chip_name: str = ""
    operator: str = ""
    temperature: str = ""
    started_at: str = ""
    finished_at: str = ""
    items: list[ItemResult] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)

    def build_summary(self) -> dict[str, Any]:
        passed = sum(1 for it in self.items if it.passed is True)
        failed = sum(1 for it in self.items if it.passed is False)
        norec = sum(1 for it in self.items if it.passed is None)
        overall = "PASS" if failed == 0 and passed > 0 else ("FAIL" if failed > 0 else "N/A")
        self.summary = {
            "total": len(self.items),
            "pass": passed,
            "fail": failed,
            "norec": norec,
            "overall": overall,
        }
        return self.summary
