# -*- coding: utf-8 -*-
"""保存结果/导出弹窗 UI 冒烟：offscreen 实例化 TestPlanPanel 与 SavedResultsDialog。

运行：.venv\\Scripts\\python.exe tests\\check_saved_results_ui.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)

    # —— TestPlanPanel：新增保存列 + 信号 ——
    from ui.models.test_plan_model import COL_COUNT, COL_SAVE, TestPlanModel
    from ui.pages.module_test._sections.test_plan_panel import TestPlanPanel

    def _fake_run(ctx):
        return {}

    registry = {
        "ldo_line_reg": ("Line Regulation", _fake_run, False, True, []),
        "ldo_ripple": ("Load Capability&Ripple", _fake_run, True, True, [1]),
    }
    panel = TestPlanPanel(registry)
    assert COL_SAVE == 7 and COL_COUNT == 8
    assert panel.model().columnCount() == 8
    header = [panel.model().headerData(c, __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.Horizontal)
              for c in range(COL_COUNT)]
    assert header[7] == "保存结果", header
    got: list[str] = []
    panel.saveResultRequested.connect(got.append)
    # 模拟点击保存列（经 proxy 索引触发 _on_clicked）
    proxy = panel._proxy
    src_idx = panel.model().index(0, COL_SAVE, panel.model().index(0, 0))
    panel._on_clicked(proxy.mapFromSource(src_idx))
    assert got == ["ldo_line_reg"], got
    # 参数列点击不触发保存信号
    src_p = panel.model().index(0, 6, panel.model().index(0, 0))
    panel._on_clicked(proxy.mapFromSource(src_p))
    assert got == ["ldo_line_reg"], got

    # —— SavedResultsDialog：默认勾选每项最新 + selected_dirs 顺序 ——
    from ui.pages.module_test.dialogs.saved_results_dialog import SavedResultsDialog

    entries = [
        {"dir": "D1", "item_key": "ldo_ripple", "name": "Ripple", "passed": True,
         "verdict": "PASS", "saved_at": "2026-09-09 10:00:00",
         "chip_name": "BES2800", "module_name": "LDO1", "test_condition": ""},
        {"dir": "D2", "item_key": "ldo_line_reg", "name": "Line Reg",
         "passed": False, "verdict": "FAIL", "saved_at": "2026-09-09 09:00:00",
         "chip_name": "BES2800", "module_name": "LDO1", "test_condition": ""},
        {"dir": "D3", "item_key": "ldo_ripple", "name": "Ripple", "passed": False,
         "verdict": "FAIL", "saved_at": "2026-09-08 08:00:00",
         "chip_name": "BES2800", "module_name": "LDO1", "test_condition": ""},
    ]
    dlg = SavedResultsDialog("ldo", entries,
                             registry_order=["ldo_line_reg", "ldo_ripple"])
    dirs = dlg.selected_dirs()
    # 注册表顺序：line_reg(D2) 在前；ripple 最新(D1) 勾选、旧(D3) 不勾
    assert dirs == ["D2", "D1"], dirs
    dlg._set_all(__import__("PySide6.QtCore", fromlist=["Qt"]).Qt.Checked)
    assert dlg.selected_dirs() == ["D2", "D1", "D3"], dlg.selected_dirs()

    print("UI SMOKE OK: 保存列/信号/弹窗默认勾选与顺序全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
