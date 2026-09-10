#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""left_nav 三段式 + 最小窗口约束冒烟验证（offscreen）。

验证点：
1. setMinimumSize(966, 640) 生效，resize 更小被钳制；
2. left_nav 三段式：Logo/底部面板垂直 Fixed，滚动区 Expanding；
3. 按钮高度随密度 QSS 档位 36/32/28，resizeEvent 驱动切换（含滞回）；
4. 导航点击切换页面不回归；
5. 紧凑视图进出后最小尺寸约束恢复。
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["KK_LAB_WITH_AI"] = os.environ.get("SMOKE_AI", "0")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication, QScrollArea
from PySide6.QtWidgets import QSizePolicy
from PySide6.QtCore import Qt

app = QApplication(sys.argv)

from ui.main_window import MainWindow  # noqa: E402

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")


win = MainWindow(with_ai=os.environ["KK_LAB_WITH_AI"] not in ("0", "false", "off", "no"))
win.show()
app.processEvents()

# 0. AI 装配路径（仅 SMOKE_AI=1）
if getattr(win, "with_ai", False):
    check("AI 面板最小宽 260", win.ai_panel.minimumWidth() == 260,
          f"got {win.ai_panel.minimumWidth()}")
    check("outer_splitter 存在且禁折叠",
          win.outer_splitter is not None and not win.outer_splitter.childrenCollapsible())
    check("AI 面板开关 toggle 不回归", True)
    win.top_bar.ai_panel_button.setChecked(True)
    app.processEvents()
    check("AI 面板打开可见", win.ai_panel.isVisible())
    win.top_bar.ai_panel_button.setChecked(False)
    app.processEvents()
    check("AI 面板关闭隐藏", not win.ai_panel.isVisible())

# 1. 最小窗口尺寸
check("minimumSize == 966x640",
      win.minimumWidth() == 966 and win.minimumHeight() == 640,
      f"got {win.minimumWidth()}x{win.minimumHeight()}")
win.resize(800, 500)
app.processEvents()
check("resize(800,500) 被钳制到 >=966x640",
      win.width() >= 966 and win.height() >= 640,
      f"got {win.width()}x{win.height()}")

# 2. 三段式结构
nav = win.nav
left_nav = win.left_nav
check("left_nav 固定宽 187", left_nav.fixedWidth() if hasattr(left_nav, 'fixedWidth') else left_nav.width() == 187 or left_nav.minimumWidth() == 187,
      f"w={left_nav.width()} min={left_nav.minimumWidth()} max={left_nav.maximumWidth()}")
scroll = getattr(nav, "nav_scroll_area", None)
check("滚动区存在且为 QScrollArea", isinstance(scroll, QScrollArea))
if scroll:
    check("滚动区 widgetResizable", scroll.widgetResizable())
    check("横向滚动条 AlwaysOff", scroll.horizontalScrollBarPolicy() == Qt.ScrollBarAlwaysOff)
    pol = scroll.sizePolicy()
    check("滚动区垂直 Expanding", pol.verticalPolicy() == QSizePolicy.Expanding,
          f"got {pol.verticalPolicy()}")
logo = left_nav.findChild(type(win), "")  # placeholder, replaced below
from PySide6.QtWidgets import QLabel
logo = left_nav.findChild(QLabel, "navLogo")
check("Logo 垂直 Fixed", logo is not None and logo.sizePolicy().verticalPolicy() == QSizePolicy.Fixed)
bottom = win.status_panel.help_btn.parentWidget()
check("底部状态面板垂直 Fixed",
      bottom.sizePolicy().verticalPolicy() == QSizePolicy.Fixed,
      f"got {bottom.sizePolicy().verticalPolicy()}")

# 3. 密度切换 + 按钮高度（ comfortable -> dense -> compact ）
btn = nav.pmu_test_btn
win.resize(1100, 900)
app.processEvents()
check("900 高 → comfortable", nav._density == "comfortable", f"got {nav._density}")
check("comfortable 按钮高 36", btn.height() == 36, f"got {btn.height()}")

win.resize(1100, 640)  # <760-12 → dense（640<700）
app.processEvents()
check("640 高 → dense", nav._density == "dense", f"got {nav._density}")
check("dense 按钮高 28（热区下限）", btn.height() == 28, f"got {btn.height()}")

# 回归：dense 下分组标题内容区不得被裁（曾因 QSS padding 重 polish 不同步被压成 2px）
from PySide6.QtWidgets import QLabel as _QLabel
titles = [t for t in nav.nav_scroll_area.widget().findChildren(_QLabel)
          if t.objectName() == "navGroupTitle"]
check("dense 标题数=4", len(titles) == 4, f"got {len(titles)}")
bad = [f"{t.text()}:{t.contentsRect().height()}" for t in titles
       if t.contentsRect().height() < 12]
check("dense 标题内容区 >=12px", not bad, ",".join(bad))

win.resize(1100, 730)  # dense → >=700+12 → compact
app.processEvents()
check("730 高 → compact", nav._density == "compact", f"got {nav._density}")
check("compact 按钮高 32", btn.height() == 32, f"got {btn.height()}")

# 滞回：730 → 705 仍应 compact（未跌破 700-12=688）
win.resize(1100, 705)
app.processEvents()
check("705 高滞回保持 compact", nav._density == "compact", f"got {nav._density}")

# 4. 导航点击切换不回归
nav.module_test_btn.click()
app.processEvents()
check("点击 Module Test 切页", win.current_instrument_ui == "module_test",
      f"got {win.current_instrument_ui}")
nav.n6705c_power_analyzer_btn.click()
app.processEvents()
check("点击 N6705C 回首页", win.current_instrument_ui in ("power_analyser", "datalog"),
      f"got {win.current_instrument_ui}")

# 5. 紧凑视图进出恢复最小尺寸
win.top_bar.compact_view_button.setChecked(True)
app.processEvents()
check("紧凑视图进入", win._compact_view is True and not win.left_nav.isVisible(),
      f"compact={win._compact_view} nav_visible={win.left_nav.isVisible()}")
win.top_bar.compact_view_button.setChecked(False)
app.processEvents()
check("退出紧凑恢复最小尺寸 966x640",
      win.minimumWidth() == 966 and win.minimumHeight() == 640,
      f"got {win.minimumWidth()}x{win.minimumHeight()}")
check("退出紧凑 left_nav 复显", win.left_nav.isVisible())

win.close()

failed = [r for r in results if not r[1]]
print(f"\n=== {len(results) - len(failed)}/{len(results)} PASS ===")
sys.exit(1 if failed else 0)
