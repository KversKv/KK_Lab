# -*- coding: utf-8 -*-
"""共享滚轮调值输入框。

统一约定：滚轮调值仅在控件聚焦时生效；未聚焦 / 禁用 / 只读时
event.ignore() 传回父级，不影响页面滚动。

- WheelLineEdit：十进制数值，固定步进（默认 0.01），双击全选。
- HexWheelLineEdit：十六进制数值，±1 / Ctrl=±0x10 / Shift=±0x100，
  按当前文本位数回绕，保留 0x 前缀与大小写风格。
- UnitWheelLineEdit：带单位后缀数值（如 100us / 50%），比例缩放 ×1.1 / ×0.9，
  保留后缀与显示精度。
"""

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit


class WheelLineEdit(QLineEdit):
    """双击全选 + 滚轮步进调值的十进制输入框。

    Qt 默认双击按"词"选择，小数点会被当作词分隔符（如 "3.8000" 双击只选中 "8000"），
    数值输入场景重写为双击即全选整框内容。
    滚轮默认以 0.01 步进调值（构造传 wheel_step= 或 set_wheel_step 可改，置 None/0 禁用）。
    """

    _DEFAULT_WHEEL_STEP = 0.01

    def __init__(self, *args, wheel_step=_DEFAULT_WHEEL_STEP, **kwargs):
        super().__init__(*args, **kwargs)
        self._wheel_step = wheel_step

    def set_wheel_step(self, step):
        """设置滚轮步进；整数字段传 1，纯文本字段传 None 禁用。"""
        self._wheel_step = step

    def wheel_step(self):
        return self._wheel_step

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selectAll()
            event.accept()
        else:
            super().mouseDoubleClickEvent(event)

    def wheelEvent(self, event):
        if (not self.hasFocus() or not self.isEnabled()
                or self.isReadOnly() or not self._wheel_step):
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.accept()
            return
        text = self.text()
        try:
            value = float(text)
        except ValueError:
            event.accept()
            return
        step = self._wheel_step
        new_value = round(value + step if delta > 0 else value - step, 6)
        # 小数位取"原文本位数"与"步进位数"的较大者，保留既有显示精度
        decimals = max(
            len(text.partition(".")[2]),
            len(f"{step:.6f}".rstrip("0").partition(".")[2]),
        )
        self.setText(f"{new_value:.{decimals}f}")
        event.accept()


class HexWheelLineEdit(QLineEdit):
    """十六进制数值输入框：滚轮 ±1，Ctrl=±0x10，Shift=±0x100。

    按当前文本的十六进制位数回绕（n 位 → mask 16**n-1），
    保留 0x/0X 前缀有无、位宽零填充与字母大小写风格；非 hex 文本不动作。
    """

    _HEX_RE = re.compile(r"^\s*(0[xX])?([0-9a-fA-F]+)\s*$")

    def wheelEvent(self, event):
        if not self.hasFocus() or not self.isEnabled() or self.isReadOnly():
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.accept()
            return
        m = self._HEX_RE.match(self.text())
        if not m:
            event.accept()
            return
        prefix, digits = m.group(1) or "", m.group(2)
        step = 1
        if event.modifiers() & Qt.ControlModifier:
            step = 0x10
        elif event.modifiers() & Qt.ShiftModifier:
            step = 0x100
        if delta < 0:
            step = -step
        mask = (16 ** len(digits)) - 1
        new_val = (int(digits, 16) + step) & mask
        # 字母大小写跟随原文本：含小写 a-f 则整体小写，否则大写
        use_lower = any(c.islower() for c in digits if c.isalpha())
        hex_str = f"{new_val:0{len(digits)}x}"
        self.setText(prefix + (hex_str if use_lower else hex_str.upper()))
        event.accept()


class UnitWheelLineEdit(QLineEdit):
    """带单位后缀数值输入框：滚轮比例缩放 ×1.1 / ×0.9，保留单位后缀。

    文本形如 "100us" / "50%" / "1.25"；无前缀数字部分不可解析时不动作。
    显示精度取原文本小数位。
    """

    _NUM_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*(.*?)\s*$")

    def wheelEvent(self, event):
        if not self.hasFocus() or not self.isEnabled() or self.isReadOnly():
            event.ignore()
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.accept()
            return
        m = self._NUM_RE.match(self.text())
        if not m:
            event.accept()
            return
        num_str, suffix = m.group(1), m.group(2)
        factor = 1.1 if delta > 0 else 0.9
        new_val = round(float(num_str) * factor, 6)
        decimals = len(num_str.partition(".")[2])
        self.setText(f"{new_val:.{decimals}f}{suffix}")
        event.accept()
