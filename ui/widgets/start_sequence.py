from PySide6.QtWidgets import QPushButton

from ui.theme.theme import load_qss

# 样式文本已迁入 ui/theme/qss/start_button.qss（W1），此处仅渲染。
START_BTN_STYLE = load_qss("start_button")


def create_start_btn(text: str = "\u25b6 START SEQUENCE") -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("primaryStartBtn")
    return btn


def update_start_btn_state(btn: QPushButton, running: bool,
                           start_text: str = "\u25b6 START SEQUENCE",
                           stop_text: str = "\u25a0 STOP"):
    btn.setEnabled(True)
    if running:
        btn.setText(stop_text)
        btn.setObjectName("stopBtn")
    else:
        btn.setText(start_text)
        btn.setObjectName("primaryStartBtn")
    btn.clearFocus()
    btn.style().unpolish(btn)
    btn.style().polish(btn)
    btn.update()
