#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Module Test 主题适配冒烟（2026-09）。

校验：
1. module_dark_tokens() 与全局 dark_tokens() 同盘（仅 name/行高差异）；
2. module_dark.qss 渲染无残留占位符、无旧 GitHub-dark 色值、LOG 覆盖段已删；
3. ModuleTestUI 实例化后顶层/两子页样式注入完整、控件结构不变。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ui.theme.theme import load_qss
from ui.theme.tokens import dark_tokens, module_dark_tokens


def check_tokens() -> None:
    d, m = dark_tokens(), module_dark_tokens()
    assert m.name == "module_dark"
    for f in ("surface_page", "surface_card", "surface_raised", "surface_input",
              "text_primary", "text_secondary", "text_muted", "text_disabled",
              "border_subtle", "border_default", "border_strong", "border_focus",
              "accent_default", "accent_hover", "accent_pressed",
              "font_ui", "font_mono"):
        assert getattr(m, f) == getattr(d, f), f
    for s in ("success", "warning", "error", "info", "running", "skipped"):
        assert getattr(m, f"state_{s}") == getattr(d, f"state_{s}"), s
    assert m.table_row_h == 34 and d.table_row_h == 26
    print("[OK] module_dark_tokens 与 dark_tokens 同盘（行高 34 保留）")


def check_qss_render() -> None:
    from ui.pages.module_test._sections.module_theme import (
        _OVERRIDES, _icon_overrides)
    text = load_qss("module_dark", module_dark_tokens(),
                    **_OVERRIDES, **_icon_overrides())
    assert "$" not in text, "存在未替换占位符"
    for legacy in ("#0E1116", "#161B22", "#1C232C", "#0C1015",
                   "#5896FF", "#3FB950", "#F85149", "#D29922"):
        assert legacy not in text, f"旧色板残留 {legacy}"
    assert "#050b1a" in text and "#5b3df5" in text
    assert "#ModuleTestShell" in text
    assert "logContainer" not in text, "LOG 覆盖段未删净"
    print("[OK] module_dark.qss 渲染：全局色值生效、无占位残留、LOG 段已删")


def check_page_build() -> None:
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    _ = app
    from ui.pages.module_test.module_test_ui import ModuleTestUI
    w = ModuleTestUI()
    assert w.objectName() == "ModuleTestShell"
    assert "CommandBar" in w.styleSheet(), "顶层缺 module_dark 顶栏规则"
    assert "QFrame#Toast" in w.styleSheet(), "顶层缺 controls 共享规则"
    for sub, name in ((w.ldo_test_ui, "ldo"), (w.dcdc_test_ui, "dcdc")):
        assert sub.objectName() == "ModuleTestSubPage", name
        assert "#ModuleTestSubPage" in sub.styleSheet(), name
    assert w.stack.count() == 2 and w.command_bar is not None
    print("[OK] ModuleTestUI 实例化：顶层/两子页样式注入完整，控件结构不变")


if __name__ == "__main__":
    check_tokens()
    check_qss_render()
    check_page_build()
    print("[PASS] Module Test 主题适配冒烟全部通过")
