from PySide6.QtWidgets import (
    QComboBox, QStyle, QStyleOptionComboBox, QListView, QStyledItemDelegate
)
from PySide6.QtCore import Qt, QRect, QRectF, QTimer
from PySide6.QtGui import QPainter, QPen, QColor, QFontMetrics, QPalette


class _ComboItemDelegate(QStyledItemDelegate):
    def __init__(self, padding_v=4, parent=None):
        super().__init__(parent)
        self._padding_v = padding_v

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        min_h = option.fontMetrics.height() + self._padding_v * 2
        if size.height() < min_h:
            size.setHeight(min_h)
        return size


class DarkComboBox(QComboBox):
    def __init__(self, *args, bg="#0F172A", border="#1E293B", arrow_color="#7b8fa5",
                 hover_color="#6366f1", **kwargs):
        super().__init__(*args, **kwargs)
        self._popup_bg = bg
        self._popup_border = border
        self._arrow_color = arrow_color
        self._hover_color = hover_color
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())
        self.setMinimumWidth(0)
        _oid = f"darkCombo_{id(self)}"
        self.setObjectName(_oid)
        self.setStyleSheet(f"""
            QComboBox#{_oid} {{
                background-color: {bg};
                border: 1.5px solid {border};
                border-radius: 6px;
                padding: 2px 28px 2px 10px;
                color: #c8d5e2;
                font-size: 13px;
                min-height: 22px;
            }}
            QComboBox#{_oid}::drop-down {{
                border: none;
                width: 22px;
            }}
            QComboBox#{_oid}::down-arrow {{
                image: none;
                width: 0px;
                height: 0px;
            }}
            QComboBox#{_oid} QLineEdit {{
                background-color: transparent;
                border: none;
                color: #c8d5e2;
                font-size: 13px;
                padding: 0px;
                margin: 0px;
            }}
            QComboBox#{_oid} QLineEdit:disabled {{
                color: #3a4a6a;
            }}
        """)
        self._setup_view(bg, border, hover_color)
        self.setMaxVisibleItems(30)

    _ITEM_PADDING_V = 4

    def _setup_view(self, bg, border, hover_color):
        list_view = QListView()
        list_view.setMouseTracking(True)
        list_view.setUniformItemSizes(True)
        list_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        delegate = _ComboItemDelegate(
            padding_v=self._ITEM_PADDING_V, parent=list_view
        )
        list_view.setItemDelegate(delegate)
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
                padding: {self._ITEM_PADDING_V}px 10px;
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        r = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        bg = QColor(self._popup_bg)
        bd = QColor(self._popup_border)
        if not self.isEnabled():
            bg = bg.darker(130)
            bd = bd.darker(130)
        painter.setPen(QPen(bd, 1.5))
        painter.setBrush(bg)
        painter.drawRoundedRect(r, 6, 6)

        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)

        if not self.isEditable():
            text_rect: QRect = self.style().subControlRect(
                QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxEditField, self
            )
            fm = QFontMetrics(self.font())
            elided = fm.elidedText(self.currentText(), Qt.ElideMiddle, text_rect.width())
            painter.setPen(QColor("#c8d5e2") if self.isEnabled() else QColor("#3a4a6a"))
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, elided)

        arrow_rect: QRect = self.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self
        )

        color = QColor(self._arrow_color)
        if not self.isEnabled():
            color = QColor("#1f315d")
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
        visible = min(self.count(), self.maxVisibleItems())
        if visible > 0:
            row_h = view.sizeHintForRow(0)
            if row_h <= 0:
                row_h = fm.height() + self._ITEM_PADDING_V * 2
            total_h = visible * row_h + 2
            view.setFixedHeight(total_h)
        no_scroll = self.count() <= self.maxVisibleItems()
        if no_scroll:
            view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        else:
            view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        super().showPopup()
        popup = view.window()
        if popup:
            if visible > 0:
                popup.setMinimumHeight(total_h)
                popup.setMaximumHeight(total_h)
            popup.setStyleSheet(
                f"background-color: {self._popup_bg}; "
                f"border: 1px solid {self._popup_border}; "
                f"padding: 0px; margin: 0px;"
            )
            if no_scroll:
                model = view.model()
                if model is not None and model.rowCount() > 0:
                    view.scrollTo(model.index(0, 0), QListView.PositionAtTop)
                    QTimer.singleShot(
                        0,
                        lambda v=view, m=model: v.scrollTo(
                            m.index(0, 0), QListView.PositionAtTop
                        ),
                    )
                self._hide_scrollers(popup)
                QTimer.singleShot(0, lambda: self._hide_scrollers(popup))

    def _hide_scrollers(self, popup):
        for child in popup.children():
            cls_name = child.metaObject().className()
            if "Scroller" in cls_name or "QComboBoxPrivateScroller" in cls_name:
                child.hide()
                child.setMaximumHeight(0)
