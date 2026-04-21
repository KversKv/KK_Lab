from PySide6.QtWidgets import QPushButton


START_BTN_STYLE = """
    QPushButton#primaryStartBtn {
        min-height: 36px;
        border-radius: 12px;
        font-size: 15px;
        font-weight: 800;
        color: white;
        border: 1px solid #645bff;
        outline: none;
        background-color: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 #5b5cf6,
            stop:1 #6a38ff
        );
    }

    QPushButton#primaryStartBtn:hover {
        background-color: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 #6b6cff,
            stop:1 #7d4cff
        );
    }

    QPushButton#primaryStartBtn:focus {
        outline: none;
    }

    QPushButton#primaryStartBtn:disabled {
        background-color: #1a2040;
        color: #4a5a80;
        border: 1px solid #1c2742;
    }

    QPushButton#stopBtn {
        min-height: 36px;
        border-radius: 12px;
        font-size: 15px;
        font-weight: 800;
        background-color: #4a1020;
        border: 1px solid #d9485f;
        color: #ffd5db;
        outline: none;
    }

    QPushButton#stopBtn:hover {
        background-color: #5a1326;
    }

    QPushButton#stopBtn:focus {
        outline: none;
    }
"""


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
