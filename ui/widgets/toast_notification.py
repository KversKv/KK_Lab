from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor, QFont

from ui.theme import Colors, Radius, Spacing, FONT_FAMILY


class ToastNotification(QWidget):

    TYPE_SUCCESS = "success"
    TYPE_ERROR = "error"
    TYPE_INFO = "info"

    _COLORS = {
        "success": {"bg": "#0a2e22", "border": "#15d1a3", "text": "#15d1a3", "icon": "\u2713"},
        "error": {"bg": "#2e0a14", "border": "#ff5e7a", "text": "#ff5e7a", "icon": "\u2717"},
        "info": {"bg": "#0a1a3e", "border": "#5b9cf5", "text": "#5b9cf5", "icon": "\u2139"},
    }

    _DURATION_MS = 2500
    _FADE_IN_MS = 150
    _FADE_OUT_MS = 300
    _SLIDE_OFFSET = 20

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedHeight(44)

        self._container = QWidget(self)
        self._container.setObjectName("toastContainer")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._container)

        inner = QHBoxLayout(self._container)
        inner.setContentsMargins(Spacing.lg, Spacing.sm, Spacing.lg, Spacing.sm)
        inner.setSpacing(Spacing.sm)

        self._icon_label = QLabel()
        self._icon_label.setFixedWidth(18)
        self._icon_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self._icon_label.setFont(font)
        inner.addWidget(self._icon_label)

        self._text_label = QLabel()
        self._text_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        inner.addWidget(self._text_label, 1)

        shadow = QGraphicsDropShadowEffect(self._container)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 100))
        self._container.setGraphicsEffect(shadow)

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self._fade_out)

        self._anim_opacity = None
        self._anim_pos = None
        self._target_pos = QPoint()

        self.hide()

    def show_toast(self, message: str, toast_type: str = "info", parent_widget=None):
        self._auto_hide_timer.stop()
        self._stop_animations()

        colors = self._COLORS.get(toast_type, self._COLORS["info"])

        self._container.setStyleSheet(f"""
            QWidget#toastContainer {{
                background-color: {colors['bg']};
                border: 1px solid {colors['border']};
                border-radius: {Radius.widget}px;
            }}
        """)
        self._icon_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['text']};
                background: transparent;
                border: none;
            }}
        """)
        self._icon_label.setText(colors["icon"])
        self._text_label.setStyleSheet(f"""
            QLabel {{
                color: {colors['text']};
                font-size: 12px;
                font-weight: 500;
                background: transparent;
                border: none;
                font-family: {FONT_FAMILY};
            }}
        """)
        self._text_label.setText(message)

        self.adjustSize()
        self.setFixedWidth(max(self.sizeHint().width() + 16, 240))

        if parent_widget is not None:
            parent_rect = parent_widget.geometry()
            global_pos = parent_widget.mapToGlobal(QPoint(0, 0))
            x = global_pos.x() + parent_rect.width() - self.width() - 20
            y = global_pos.y() + parent_rect.height() - self.height() - 20
            self._target_pos = QPoint(x, y)
        else:
            self._target_pos = QPoint(100, 100)

        self._fade_in()

    def _fade_in(self):
        self._stop_animations()
        self.setWindowOpacity(0.0)

        start_pos = QPoint(self._target_pos.x(), self._target_pos.y() + self._SLIDE_OFFSET)
        self.move(start_pos)
        super().show()
        self.raise_()

        self._anim_opacity = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_opacity.setDuration(self._FADE_IN_MS)
        self._anim_opacity.setStartValue(0.0)
        self._anim_opacity.setEndValue(1.0)
        self._anim_opacity.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_pos = QPropertyAnimation(self, b"pos", self)
        self._anim_pos.setDuration(self._FADE_IN_MS)
        self._anim_pos.setStartValue(start_pos)
        self._anim_pos.setEndValue(self._target_pos)
        self._anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        self._anim_opacity.start()
        self._anim_pos.start()

        self._auto_hide_timer.start(self._DURATION_MS)

    def _fade_out(self):
        self._stop_animations()

        self._anim_opacity = QPropertyAnimation(self, b"windowOpacity", self)
        self._anim_opacity.setDuration(self._FADE_OUT_MS)
        self._anim_opacity.setStartValue(self.windowOpacity())
        self._anim_opacity.setEndValue(0.0)
        self._anim_opacity.setEasingCurve(QEasingCurve.InCubic)
        self._anim_opacity.finished.connect(self._on_fade_out_done)
        self._anim_opacity.start()

    def _on_fade_out_done(self):
        self.setWindowOpacity(1.0)
        self.hide()

    def _stop_animations(self):
        for anim in (self._anim_opacity, self._anim_pos):
            if anim is None:
                continue
            try:
                if anim.state() == QPropertyAnimation.Running:
                    anim.stop()
            except RuntimeError:
                pass
        self._anim_opacity = None
        self._anim_pos = None
