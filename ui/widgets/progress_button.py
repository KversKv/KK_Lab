import os
from ui.resource_path import get_resource_base

from PySide6.QtWidgets import QWidget, QToolTip
from PySide6.QtCore import (
    Qt, QTimer, Signal, QSize,
    QRectF, QRect, QPropertyAnimation, QEasingCurve, Property,
    QElapsedTimer as _QElapsedTimer
)
from PySide6.QtGui import (
    QFont, QPixmap, QPainter, QColor, QPen,
    QFontMetrics, QPainterPath, QCursor
)
from PySide6.QtSvg import QSvgRenderer

_ICONS_DIR = os.path.join(
    get_resource_base(),
    "resources", "icons"
)


class ProgressButton(QWidget):
    clicked = Signal()
    stop_clicked = Signal()

    STATE_IDLE = "idle"
    STATE_WAITING = "waiting"
    STATE_PROGRAMMING = "programming"
    STATE_COMPLETE = "complete"
    STATE_FAILED = "failed"

    DEFAULT_STYLE = {
        "bg": "#162544",
        "border": "#25355c",
        "radius": 8.0,
        "text_color": "#dbe7ff",
        "progress_color": (93, 69, 255, 60),
        "complete_bg": (13, 107, 79, 80),
        "complete_text_color": "#4ade80",
        "failed_bg": "#2a0f1a",
        "failed_border": "#6b2040",
        "failed_text_color": "#ff7593",
        "waiting_text_color": "#a0b4d8",
        "spinner_color": (93, 69, 255, 200),
        "spinner_width": 2.5,
        "separator_color": "#25355c",
        "stop_color_normal": "#8a9bbe",
        "stop_color_hover": "#ff5a5a",
        "stop_hover_bg": (255, 70, 70, 40),
        "stop_zone_width": 38,
        "min_height": 48,
        "font_weight": QFont.DemiBold,
        "font_family": None,
        "font_size_pt": None,
    }

    def __init__(
        self,
        idle_text="Program DUT",
        waiting_text="Wait for sync",
        programming_text="Programming",
        complete_text="\u2713  Program complete",
        failed_text="Program failed",
        icon_path=None,
        baud_rate=921600,
        style_overrides=None,
        parent=None,
    ):
        super().__init__(parent)

        self._idle_text = idle_text
        self._waiting_text = waiting_text
        self._programming_text = programming_text
        self._complete_text = complete_text
        self._failed_text = failed_text
        self._baud_rate = baud_rate

        self._style = dict(self.DEFAULT_STYLE)
        if style_overrides:
            self._style.update(style_overrides)

        self._state = self.STATE_IDLE
        self._progress = 0.0
        self._file_size = 0
        self._stop_hovered = False
        self._spinner_angle = 0.0

        self.setMinimumHeight(self._style["min_height"])
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)

        if icon_path is None:
            icon_path = os.path.join(_ICONS_DIR, "download.svg")
        self._icon_svg = QSvgRenderer(icon_path) if os.path.isfile(icon_path) else None

        self._spinner_timer = QTimer(self)
        self._spinner_timer.setInterval(30)
        self._spinner_timer.timeout.connect(self._tick_spinner)

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(50)
        self._progress_timer.timeout.connect(self._tick_progress)
        self._elapsed = _QElapsedTimer()

        self._reset_timer = QTimer(self)
        self._reset_timer.setSingleShot(True)
        self._reset_timer.timeout.connect(self._reset_to_idle)

    def state(self):
        return self._state

    def setFileSize(self, size_bytes):
        self._file_size = size_bytes

    def setStateIdle(self):
        self._state = self.STATE_IDLE
        self._progress = 0.0
        self._spinner_timer.stop()
        self._progress_timer.stop()
        self._reset_timer.stop()
        self.setCursor(Qt.PointingHandCursor)
        self.update()

    def setStateWaiting(self):
        self._state = self.STATE_WAITING
        self._progress = 0.0
        self._spinner_angle = 0.0
        self._spinner_timer.start()
        self._progress_timer.stop()
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def setStateProgramming(self):
        self._state = self.STATE_PROGRAMMING
        self._progress = 0.0
        self._spinner_timer.stop()
        self._elapsed.start()
        self._progress_timer.start()
        self.setCursor(Qt.ArrowCursor)
        self.update()

    def setStateComplete(self):
        self._state = self.STATE_COMPLETE
        self._progress = 1.0
        self._spinner_timer.stop()
        self._progress_timer.stop()
        self.setCursor(Qt.ArrowCursor)
        self.update()
        self._reset_timer.start(1500)

    def setStateFailed(self):
        self._state = self.STATE_FAILED
        self._progress = 0.0
        self._spinner_timer.stop()
        self._progress_timer.stop()
        self.setCursor(Qt.ArrowCursor)
        self.update()
        self._reset_timer.start(2000)

    def setProgress(self, value):
        self._progress = max(0.0, min(1.0, value))
        self.update()

    def _reset_to_idle(self):
        self.setStateIdle()

    def _tick_spinner(self):
        self._spinner_angle = (self._spinner_angle + 8.0) % 360.0
        self.update()

    def _tick_progress(self):
        if self._file_size <= 0:
            return
        elapsed_s = self._elapsed.elapsed() / 1000.0
        bytes_per_sec = self._baud_rate / 10.0
        transferred = elapsed_s * bytes_per_sec
        self._progress = min(transferred / self._file_size, 0.98)
        self.update()

    def _stop_rect(self):
        stop_w = self._style["stop_zone_width"]
        return QRect(self.width() - stop_w, 0, stop_w, self.height())

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            return super().mousePressEvent(event)
        if self._state == self.STATE_PROGRAMMING:
            if self._stop_rect().contains(event.pos()):
                self.stop_clicked.emit()
        elif self._state == self.STATE_IDLE:
            self.clicked.emit()

    def mouseMoveEvent(self, event):
        if self._state == self.STATE_PROGRAMMING:
            in_stop = self._stop_rect().contains(event.pos())
            if in_stop != self._stop_hovered:
                self._stop_hovered = in_stop
                self.setCursor(Qt.PointingHandCursor if in_stop else Qt.ArrowCursor)
                if in_stop:
                    QToolTip.showText(QCursor.pos(), "Stop")
                self.update()
        else:
            self._stop_hovered = False
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._stop_hovered:
            self._stop_hovered = False
            self.update()
        super().leaveEvent(event)

    @staticmethod
    def _to_qcolor(val):
        if isinstance(val, QColor):
            return val
        if isinstance(val, (tuple, list)):
            return QColor(*val)
        return QColor(val)

    def _build_font(self):
        s = self._style
        font = QFont(self.font())
        font.setWeight(s["font_weight"])
        if s["font_family"]:
            font.setFamily(s["font_family"])
        if s["font_size_pt"]:
            font.setPointSize(s["font_size_pt"])
        return font

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        s = self._style
        w, h = self.width(), self.height()
        radius = s["radius"]
        stop_w = s["stop_zone_width"]

        if self._state == self.STATE_FAILED:
            bg = self._to_qcolor(s["failed_bg"])
            border = self._to_qcolor(s["failed_border"])
        else:
            bg = self._to_qcolor(s["bg"])
            border = self._to_qcolor(s["border"])

        btn_path = QPainterPath()
        btn_path.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
        p.setPen(QPen(border, 1))
        p.setBrush(bg)
        p.drawPath(btn_path)

        if self._state == self.STATE_PROGRAMMING:
            fill_w = max(0, (w - stop_w) * self._progress)
            if fill_w > 0:
                clip = QPainterPath()
                clip.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
                p.save()
                p.setClipPath(clip)
                p.setPen(Qt.NoPen)
                p.setBrush(self._to_qcolor(s["progress_color"]))
                p.drawRect(QRectF(0, 0, fill_w, h))
                p.restore()
        elif self._state == self.STATE_COMPLETE:
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
            p.save()
            p.setClipPath(clip)
            p.setPen(Qt.NoPen)
            p.setBrush(self._to_qcolor(s["complete_bg"]))
            p.drawRect(QRectF(0, 0, w, h))
            p.restore()

        font = self._build_font()
        p.setFont(font)
        fm = QFontMetrics(font)

        icon_size = 18
        icon_text_gap = 6

        if self._state == self.STATE_IDLE:
            self._paint_idle(p, fm, w, h, icon_size, icon_text_gap, s)
        elif self._state == self.STATE_WAITING:
            self._paint_waiting(p, fm, w, h, icon_size, icon_text_gap, s)
        elif self._state == self.STATE_PROGRAMMING:
            self._paint_programming(p, fm, w, h, stop_w, radius, s)
        elif self._state == self.STATE_COMPLETE:
            self._paint_complete(p, fm, w, h, s)
        elif self._state == self.STATE_FAILED:
            self._paint_failed(p, fm, w, h, s)

        p.end()

    def _paint_idle(self, p, fm, w, h, icon_size, icon_text_gap, s):
        text = self._idle_text
        text_color = self._to_qcolor(s["text_color"])
        tw = fm.horizontalAdvance(text)
        total_w = (icon_size + icon_text_gap + tw) if self._icon_svg else tw
        start_x = (w - total_w) / 2

        if self._icon_svg:
            tinted = QPixmap(icon_size, icon_size)
            tinted.fill(Qt.transparent)
            tp = QPainter(tinted)
            tp.setRenderHint(QPainter.Antialiasing)
            tp.setRenderHint(QPainter.SmoothPixmapTransform)
            self._icon_svg.render(tp, QRectF(0, 0, icon_size, icon_size))
            tp.setCompositionMode(QPainter.CompositionMode_SourceIn)
            tp.fillRect(tinted.rect(), text_color)
            tp.end()
            p.drawPixmap(int(start_x), int((h - icon_size) / 2), tinted)
            text_x = start_x + icon_size + icon_text_gap
        else:
            text_x = start_x

        p.setPen(text_color)
        p.drawText(QRectF(text_x, 0, tw + 2, h),
                   Qt.AlignVCenter | Qt.AlignLeft, text)

    def _paint_waiting(self, p, fm, w, h, icon_size, icon_text_gap, s):
        text = self._waiting_text
        text_color = self._to_qcolor(s["waiting_text_color"])
        tw = fm.horizontalAdvance(text)
        total_w = icon_size + icon_text_gap + tw
        start_x = (w - total_w) / 2

        cx = start_x + icon_size / 2
        cy = h / 2
        p.save()
        p.translate(cx, cy)
        p.rotate(self._spinner_angle)
        pen = QPen(self._to_qcolor(s["spinner_color"]), s["spinner_width"])
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(QRectF(-icon_size / 2, -icon_size / 2, icon_size, icon_size),
                  0 * 16, 270 * 16)
        p.restore()

        p.setPen(text_color)
        p.drawText(QRectF(start_x + icon_size + icon_text_gap, 0, tw + 2, h),
                   Qt.AlignVCenter | Qt.AlignLeft, text)

    def _paint_programming(self, p, fm, w, h, stop_w, radius, s):
        pct = int(self._progress * 100)
        text_color = self._to_qcolor(s["text_color"])
        main_w = w - stop_w

        prefix = f"{self._programming_text} "
        suffix = "%"
        max_num = "100"
        max_full = prefix + max_num + suffix
        max_tw = fm.horizontalAdvance(max_full)
        anchor_x = (main_w - max_tw) / 2

        prefix_w = fm.horizontalAdvance(prefix)
        max_num_w = fm.horizontalAdvance(max_num)
        num_str = str(pct)

        p.setPen(text_color)
        p.drawText(QRectF(anchor_x, 0, prefix_w, h),
                   Qt.AlignVCenter | Qt.AlignLeft, prefix)
        p.drawText(QRectF(anchor_x + prefix_w, 0, max_num_w, h),
                   Qt.AlignVCenter | Qt.AlignRight, num_str)
        p.drawText(QRectF(anchor_x + prefix_w + max_num_w, 0,
                          fm.horizontalAdvance(suffix) + 2, h),
                   Qt.AlignVCenter | Qt.AlignLeft, suffix)

        sep_x = w - stop_w
        p.setPen(QPen(self._to_qcolor(s["separator_color"]), 1))
        p.drawLine(int(sep_x), 4, int(sep_x), h - 4)

        stop_rect = self._stop_rect()
        if self._stop_hovered:
            p.save()
            clip = QPainterPath()
            clip.addRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), radius, radius)
            p.setClipPath(clip)
            p.setPen(Qt.NoPen)
            p.setBrush(self._to_qcolor(s["stop_hover_bg"]))
            p.drawRect(stop_rect)
            p.restore()

        stop_icon_s = 12
        six = stop_rect.x() + (stop_rect.width() - stop_icon_s) / 2
        siy = (h - stop_icon_s) / 2
        stop_color = self._to_qcolor(s["stop_color_hover"]) if self._stop_hovered else self._to_qcolor(s["stop_color_normal"])
        p.setPen(Qt.NoPen)
        p.setBrush(stop_color)
        p.drawRoundedRect(QRectF(six, siy, stop_icon_s, stop_icon_s), 2, 2)

    def _paint_complete(self, p, fm, w, h, s):
        text_color = self._to_qcolor(s["complete_text_color"])
        p.setPen(text_color)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self._complete_text)

    def _paint_failed(self, p, fm, w, h, s):
        text_color = self._to_qcolor(s["failed_text_color"])
        p.setPen(text_color)
        p.drawText(QRectF(0, 0, w, h), Qt.AlignCenter, self._failed_text)

    def sizeHint(self):
        return QSize(220, self._style["min_height"])
