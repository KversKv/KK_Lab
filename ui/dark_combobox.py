from PySide6.QtWidgets import QComboBox


class DarkComboBox(QComboBox):
    def __init__(self, *args, bg="#0a1733", border="#27406f", **kwargs):
        super().__init__(*args, **kwargs)
        self._popup_bg = bg
        self._popup_border = border
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

    def showPopup(self):
        super().showPopup()
        popup = self.view().window()
        if popup:
            popup.setStyleSheet(
                f"background-color: {self._popup_bg}; "
                f"border: 1px solid {self._popup_border}; "
                f"padding: 0px; margin: 0px;"
            )
