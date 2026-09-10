#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共享滚轮输入框（ui/widgets/wheel_line_edit.py）行为校验。

用例：
  A. WheelLineEdit：聚焦步进 / 未聚焦忽略 / 整数步进 / 非数值不动作 /
     禁用步进 / 显示精度保留；
  B. HexWheelLineEdit：±1 / Ctrl±0x10 / Shift±0x100 / 位宽回绕 /
     大小写与前缀风格保留 / 未聚焦忽略；
  C. UnitWheelLineEdit：带单位比例缩放 / 无后缀纯数 / 非数值不动作；
  D. SelectAllLineEdit（n6705c）继承共享实现后行为不变。

用法：.venv\\Scripts\\python.exe tests\\check_wheel_line_edit.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, Qt  # noqa: E402
from PySide6.QtGui import QWheelEvent  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ui.widgets.wheel_line_edit import (  # noqa: E402
    HexWheelLineEdit, UnitWheelLineEdit, WheelLineEdit,
)
from ui.pages.n6705c_power_analyzer.widgets import SelectAllLineEdit  # noqa: E402

FAILURES: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


def wheel(widget, delta_y=120, modifiers=Qt.NoModifier):
    ev = QWheelEvent(QPointF(1, 1), QPointF(1, 1), QPoint(0, 0), QPoint(0, delta_y),
                     Qt.NoButton, modifiers, Qt.ScrollPhase.NoScrollPhase, False)
    widget.wheelEvent(ev)
    return ev.isAccepted()


def focused(widget):
    widget.show()
    widget.setFocus()
    app.processEvents()
    assert widget.hasFocus(), f"focus acquire failed: {widget}"


app = QApplication([])

# ---- A. WheelLineEdit ----
w = WheelLineEdit("3.80")
focused(w)
check("A1 聚焦滚轮上滚 +0.01", wheel(w) and w.text() == "3.81", w.text())
check("A2 聚焦滚轮下滚 -0.01", wheel(w, -120) and w.text() == "3.80", w.text())

w2 = WheelLineEdit("9.99")
w2.show()
app.processEvents()
accepted = wheel(w2)
check("A3 未聚焦忽略且事件传父级", (not accepted) and w2.text() == "9.99",
      f"accepted={accepted} text={w2.text()}")

w3 = WheelLineEdit("5", wheel_step=1)
focused(w3)
check("A4 整数步进 +1", wheel(w3) and w3.text() == "6", w3.text())

w4 = WheelLineEdit("abc")
focused(w4)
check("A5 非数值文本不动作但消费事件", wheel(w4) and w4.text() == "abc", w4.text())

w5 = WheelLineEdit("1.00", wheel_step=None)
focused(w5)
accepted5 = wheel(w5)
check("A6 步进 None 禁用且事件传父级", (not accepted5) and w5.text() == "1.00",
      f"accepted={accepted5} text={w5.text()}")

w6 = WheelLineEdit("0.800")
focused(w6)
check("A7 显示精度保留（原文本 3 位）", wheel(w6) and w6.text() == "0.810", w6.text())

# ---- B. HexWheelLineEdit ----
h = HexWheelLineEdit("0x57")
focused(h)
check("B1 滚轮 +1", wheel(h) and h.text() == "0x58", h.text())
check("B2 滚轮 -1", wheel(h, -120) and h.text() == "0x57", h.text())

h2 = HexWheelLineEdit("0xFF")
focused(h2)
check("B3 位宽回绕 0xFF+1=0x00", wheel(h2) and h2.text() == "0x00", h2.text())
check("B4 位宽回绕 0x00-1=0xFF", wheel(h2, -120) and h2.text() == "0xFF", h2.text())

h3 = HexWheelLineEdit("0x57")
focused(h3)
check("B5 Ctrl 步进 +0x10", wheel(h3, modifiers=Qt.ControlModifier) and h3.text() == "0x67",
      h3.text())

h4 = HexWheelLineEdit("0x0135")
focused(h4)
check("B6 Shift 步进 +0x100 且零填充位宽不变",
      wheel(h4, modifiers=Qt.ShiftModifier) and h4.text() == "0x0235", h4.text())

h5 = HexWheelLineEdit("0x033b")
focused(h5)
check("B7 小写风格保留", wheel(h5) and h5.text() == "0x033c", h5.text())

h6 = HexWheelLineEdit("1A")
focused(h6)
check("B8 无 0x 前缀保留", wheel(h6) and h6.text() == "1B", h6.text())

h7 = HexWheelLineEdit("0x6A")
h7.show()
app.processEvents()
accepted7 = wheel(h7)
check("B9 未聚焦忽略", (not accepted7) and h7.text() == "0x6A",
      f"accepted={accepted7} text={h7.text()}")

# ---- C. UnitWheelLineEdit ----
u = UnitWheelLineEdit("100us")
focused(u)
check("C1 带单位上滚 ×1.1", wheel(u) and u.text() == "110us", u.text())
check("C2 带单位下滚 ×0.9", wheel(u, -120) and u.text() == "99us", u.text())

u2 = UnitWheelLineEdit("50")
focused(u2)
check("C3 无后缀纯数 ×1.1", wheel(u2) and u2.text() == "55", u2.text())

u3 = UnitWheelLineEdit("abc")
focused(u3)
check("C4 非数值不动作", wheel(u3) and u3.text() == "abc", u3.text())

# ---- D. SelectAllLineEdit 兼容 ----
s = SelectAllLineEdit("1.00")
focused(s)
check("D1 SelectAllLineEdit 滚轮行为不变", wheel(s) and s.text() == "1.01", s.text())
check("D2 SelectAllLineEdit 是 WheelLineEdit 子类", isinstance(s, WheelLineEdit))

print()
if FAILURES:
    print(f"FAILED: {len(FAILURES)} 项 — {FAILURES}")
    sys.exit(1)
print("ALL PASS")
