"""GPADC 页内私有滑动开关（iOS 风格，36x20，150ms 滑块动画）。

从 ui/pages/pmu_test/gpadc_test_ui.py 平移而来，行为零变更。"""

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QBrush, QPainter


class _ToggleSwitch(QWidget):
    """页面私有滑动开关（iOS 风格，36x20，150ms 滑块动画）。"""

    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self._thumb_pos = 1.0 if checked else 0.0
        self.setFixedSize(36, 20)
        self.setCursor(Qt.PointingHandCursor)

        self._anim = QPropertyAnimation(self, b"thumb_pos")
        self._anim.setDuration(150)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_thumb_pos(self):
        return self._thumb_pos

    def _set_thumb_pos(self, val):
        self._thumb_pos = val
        self.update()

    thumb_pos = Property(float, _get_thumb_pos, _set_thumb_pos)

    def isChecked(self):
        return self._checked

    def setChecked(self, val):
        if val == self._checked:
            return
        self._checked = val
        self._anim.stop()
        self._anim.setStartValue(self._thumb_pos)
        self._anim.setEndValue(1.0 if val else 0.0)
        self._anim.start()
        self.toggled.emit(val)

    def mousePressEvent(self, event):
        self.setChecked(not self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        radius = h / 2.0

        track_color = QColor("#5b5cf6") if self._checked else QColor("#2a3555")
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(0, 0, w, h, radius, radius)

        thumb_r = h - 6
        x = 3 + self._thumb_pos * (w - thumb_r - 6)
        y = 3
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawEllipse(int(x), int(y), int(thumb_r), int(thumb_r))
        p.end()
