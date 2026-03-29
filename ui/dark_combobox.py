from PySide6.QtWidgets import QComboBox


class DarkComboBox(QComboBox):
    def __init__(self, *args, bg="#0a1733", border="#27406f", **kwargs):
        super().__init__(*args, **kwargs)
        self._popup_bg = bg
        self._popup_border = border
        self._apply_popup_style()

    def _apply_popup_style(self):
        ss = (
            f"background-color: {self._popup_bg}; "
            f"border: 1px solid {self._popup_border};"
        )
        self.view().window().setStyleSheet(ss)
        self.view().setStyleSheet(
            f"background-color: {self._popup_bg}; "
            f"color: #eaf2ff; "
            f"selection-background-color: #334a7d; "
            f"outline: 0px;"
        )

    def showPopup(self):
        super().showPopup()
        popup = self.view().window()
        if popup:
            popup.setStyleSheet(
                f"background-color: {self._popup_bg}; "
                f"border: 1px solid {self._popup_border};"
            )
            global_pos = self.mapToGlobal(self.rect().bottomLeft())
            popup.move(global_pos.x(), global_pos.y())
