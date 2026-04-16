from PySide6.QtWidgets import QComboBox, QStyle, QStyleOptionComboBox, QListView
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QPen, QColor, QFontMetrics, QPalette


class DarkComboBox(QComboBox):
    def __init__(self, *args, bg="#0a1733", border="#27406f", arrow_color="#7B8CB7",
                 hover_color="#5d45ff", **kwargs):
        super().__init__(*args, **kwargs)
        self._popup_bg = bg
        self._popup_border = border
        self._arrow_color = arrow_color
        self._hover_color = hover_color
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())
        self.setMinimumWidth(0)
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
            QComboBox QLineEdit {{
                background-color: transparent;
                border: none;
                color: #c8d8f8;
                font-size: 13px;
                padding: 0px;
                margin: 0px;
            }}
            QComboBox QLineEdit:disabled {{
                color: #5c7096;
            }}
        """)
        self._setup_view(bg, border, hover_color)
        self.setMaxVisibleItems(30)

    def _setup_view(self, bg, border, hover_color):
        list_view = QListView()
        list_view.setMouseTracking(True)
        palette = list_view.palette()
        palette.setColor(QPalette.Highlight, QColor(hover_color))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        list_view.setPalette(palette)
        list_view.setStyleSheet(f"""
            QListView {{
                background-color: {bg};
                color: #eaf2ff;
                border: 1px solid {border};
                outline: 0;
            }}
            QListView::item {{
                padding: 4px 10px;
                border: none;
            }}
            QListView::item:hover {{
                background-color: {hover_color};
                color: white;
            }}
            QListView::item:selected {{
                background-color: {hover_color};
                color: white;
                border: none;
                outline: none;
            }}
        """)
        self.setView(list_view)

    def paintEvent(self, event):
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        opt.currentText = ""

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        self.style().drawComplexControl(QStyle.CC_ComboBox, opt, painter, self)

        if not self.isEditable():
            text_rect: QRect = self.style().subControlRect(
                QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxEditField, self
            )
            fm = QFontMetrics(self.font())
            elided = fm.elidedText(self.currentText(), Qt.ElideMiddle, text_rect.width())
            painter.setPen(QColor("#c8d8f8") if self.isEnabled() else QColor("#5c7096"))
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        arrow_rect: QRect = self.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self
        )

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
