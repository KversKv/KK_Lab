from PySide6.QtWidgets import QComboBox, QStyle, QStyleOptionComboBox
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QPen, QColor


class DarkComboBox(QComboBox):
    def __init__(self, *args, bg="#0a1733", border="#27406f", arrow_color="#7B8CB7", **kwargs):
        super().__init__(*args, **kwargs)
        self._popup_bg = bg
        self._popup_border = border
        self._arrow_color = arrow_color
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {bg};
                border: 1.5px solid {border};
                border-radius: 6px;
                padding: 4px 28px 4px 10px;
                color: #c8d8f8;
                font-size: 13px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {bg};
                color: #eaf2ff;
                border: 1px solid {border};
                selection-background-color: #334a7d;
                outline: 0;
                padding: 0px;
                margin: 0px;
            }}
            QComboBox QAbstractItemView::item {{
                background-color: {bg};
                color: #eaf2ff;
                padding: 4px 10px;
                border: none;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: #334a7d;
            }}
        """)
        self.setMaxVisibleItems(30)

    def paintEvent(self, event):
        super().paintEvent(event)

        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        arrow_rect: QRect = self.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self
        )

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        color = QColor(self._arrow_color)
        if not self.isEnabled():
            color = QColor("#3A4563")
        pen = QPen(color, 1.6)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)

        cx = arrow_rect.center().x()
        cy = arrow_rect.center().y()
        half_w = 4
        half_h = 3

        painter.drawLine(cx - half_w, cy - half_h, cx, cy + half_h)
        painter.drawLine(cx, cy + half_h, cx + half_w, cy - half_h)

        painter.end()

    def showPopup(self):
        view = self.view()
        fm = self.fontMetrics()
        max_w = self.width()
        for i in range(self.count()):
            w = fm.horizontalAdvance(self.itemText(i)) + 40
            if w > max_w:
                max_w = w
        view.setMinimumWidth(max_w)
        super().showPopup()
        popup = view.window()
        if popup:
            popup.setStyleSheet(
                f"background-color: {self._popup_bg}; "
                f"border: 1px solid {self._popup_border}; "
                f"padding: 0px; margin: 0px;"
            )
